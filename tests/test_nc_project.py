import json,os,tempfile,time,unittest,zipfile
from pathlib import Path
from backend.server import Application
from backend.nc_project import ROOT_CMAKE,retire_legacy_cmake
from backend.preferences import atomic_json
from backend.nc_project_bridge import imports

ROOT=Path(__file__).resolve().parents[1]
MAIN='use <project:helper>; use <io:output>; app :: runtime { fn: run() -> bool { println(helper.worker.answer()); return true; } ref main ->> run; fa: return true; }'
HELPER='worker :: runtime { fn: public: answer() -> int { return 42; } fa: return true; }'
class NcProjects(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=self.base/'Project with spaces';self.root.mkdir()
  self.app=Application(ROOT,self.root,data_dir=self.base/'profile');self.ws=self.app.workspace;self.ws.trusted=True
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def execute(self,plan):
  job=self.app.runner.jobs[self.app.runner.start(plan['commands'],self.root,timeout=60)['job']];end=time.monotonic()+70
  while not job.done and time.monotonic()<end:time.sleep(.03)
  self.assertTrue(job.done);self.assertEqual(job.code,0,job.output);return job.output
 def test_module_check_and_run_use_ncc_project_without_relocating_user_sources(self):
  (self.root/'main.n').write_text(MAIN);(self.root/'Helper.n').write_text(HELPER)
  rt=self.app.features.runtimes;plan=rt.plan(self.ws,'main.n')
  self.assertEqual(plan['projectMode'],'ncc-project-runtime');self.assertIsNone(plan['artifacts']['cmake'])
  self.assertIn('42',self.execute(plan));self.execute(rt.plan(self.ws,'main.n',check=True))
  self.assertFalse((self.root/'src').exists());self.assertFalse(list(self.root.rglob('CMakeLists.txt')))
  self.assertEqual((self.root/'Helper.n').read_text(),HELPER)
  build=rt.plan(self.ws,'main.n',build_only=True);self.assertEqual(len(build['commands']),1);self.assertIn('build',build['commands'][0]);self.assertTrue(build['nativeLinkRequired'])
 def test_module_program_accepts_live_input_in_a_real_terminal(self):
  main='use <project:helper>; use <io:input, output>; app :: runtime { fn: run() -> bool { println("READY>"); value >> str <- readLine(); println(value); println(helper.worker.answer()); return true; } ref main ->> run; fa: return true; }'
  (self.root/'main.n').write_text(main);(self.root/'Helper.n').write_text(HELPER)
  result=self.app.features.hacker.start(self.ws,'main.n',main,'file')
  terminal=self.app.features.terminals.get(result['terminal']['id'])
  try:
   end=time.monotonic()+30
   while 'READY>' not in terminal.output and not terminal.closed and time.monotonic()<end:time.sleep(.03)
   self.assertIn('READY>',terminal.output);self.assertFalse(terminal.closed)
   self.assertTrue(terminal.write('LIVE_INPUT_928\r'))
   end=time.monotonic()+10
   while not terminal.closed and time.monotonic()<end:time.sleep(.03)
   self.assertTrue(terminal.closed,terminal.output);self.assertEqual(terminal.code,0,terminal.output)
   # One echo from the console and one from the program. Seeing only an echo
   # would miss the Windows inherited-console regression.
   self.assertIn('LIVE_INPUT_928',terminal.output);self.assertIn('42',terminal.output)
   self.assertEqual((self.root/'main.n').read_text(),main)
  finally:terminal.close()
 def test_module_program_accepts_delayed_pipe_input(self):
  main='use <project:helper>; use <io:input, output>; app :: runtime { fn: run() -> bool { println("PIPE_READY>"); value >> str <- readLine(); println(value); println(helper.worker.answer()); return true; } ref main ->> run; fa: return true; }'
  (self.root/'main.n').write_text(main);(self.root/'Helper.n').write_text(HELPER)
  plan=self.app.features.runtimes.plan(self.ws,'main.n')
  job=self.app.runner.jobs[self.app.runner.start(plan['commands'],self.root,timeout=35)['job']]
  try:
   end=time.monotonic()+30
   while 'PIPE_READY>' not in job.output and not job.done and time.monotonic()<end:time.sleep(.03)
   self.assertIn('PIPE_READY>',job.output);self.assertFalse(job.done)
   job.write('PIPE_INPUT_731\n')
   end=time.monotonic()+10
   while not job.done and time.monotonic()<end:time.sleep(.03)
   self.assertTrue(job.done,job.output);self.assertEqual(job.code,0,job.output)
   self.assertIn('PIPE_INPUT_731',job.output);self.assertIn('42',job.output)
  finally:
   if not job.done:job.cancel()
 @unittest.skipUnless(os.name=='nt','MSVC host linker')
 def test_native_module_build_uses_complete_installed_msvc_libraries(self):
  from backend.windows_toolchain import native_environment
  if not native_environment(os.environ).get('LIB'):self.skipTest('MSVC libraries are not installed')
  (self.root/'main.n').write_text(MAIN);(self.root/'Helper.n').write_text(HELPER)
  plan=self.app.features.runtimes.plan(self.ws,'main.n',build_only=True)
  self.execute(plan);self.assertTrue(plan['target'].is_file())
  self.assertIn('42',self.execute({'commands':[[str(plan['target'])]]}))
 def test_library_discovery_skips_partial_newer_toolsets(self):
  from backend.windows_toolchain import complete_libraries
  install=self.base/'VS';kits=self.base/'Kits'
  for name in ('legacy_stdio_definitions.lib','msvcrt.lib','vcruntime.lib'):
   p=install/'VC/Tools/MSVC/14.44/lib/x64'/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
  (install/'VC/Tools/MSVC/14.51/lib/x64').mkdir(parents=True)
  for name in ('ucrt/x64/ucrt.lib','um/x64/kernel32.lib'):
   p=kits/'Lib/10.0.28000'/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
  (kits/'Lib/10.0.29000').mkdir()
  paths=complete_libraries(install,kits)
  self.assertEqual(paths[0],install/'VC/Tools/MSVC/14.44/lib/x64');self.assertIn('10.0.28000',str(paths[1]))
 def test_explicit_library_environment_is_preserved(self):
  from backend.windows_toolchain import native_environment
  env={'LIB':'my-selected-toolchain','PATH':'unchanged'}
  self.assertEqual(native_environment(env),env)
 def test_project_diagnostics_use_pending_dependencies_and_reject_real_errors(self):
  from backend.nc_diagnostics import check
  (self.root/'main.n').write_text(MAIN);(self.root/'Helper.n').write_text('')
  backup=self.ws.private_dir('backups')/'old.n';backup.write_text(MAIN)
  self.app.features.workbenches.checkpoint(self.ws,{'session':{'documents':[{'path':'Helper.n','dirty':True,'content':HELPER}],'active':'Helper.n'}})
  result=check(self.app.features,self.ws,{'path':'main.n','text':MAIN})
  self.assertEqual(result['code'],0,result);self.assertEqual(result['authority'],'ncc-project-check')
  count=len(self.app.runner.jobs);self.assertEqual(check(self.app.features,self.ws,{'path':'main.n','text':MAIN}),result)
  self.assertEqual(len(self.app.runner.jobs),count)
  broken=check(self.app.features,self.ws,{'path':'main.n','text':MAIN.replace('answer()','missing()')})
  self.assertNotEqual(broken['code'],0);self.assertIn('error[',broken['output'])
  library=check(self.app.features,self.ws,{'path':'Helper.n','text':HELPER})
  self.assertEqual(library['code'],0,library)
  self.assertEqual((self.root/'Helper.n').read_text(),'');self.assertEqual(backup.read_text(),MAIN)
 def test_project_diagnostic_command_is_reserved_to_the_nc_adapter(self):
  from types import SimpleNamespace
  with self.assertRaises(PermissionError):self.app.features.extension_services.call(SimpleNamespace(extension_id='other.extension',workspace=self.ws), 'command.execute',{'id':'zenit.nc.projectDiagnostics','args':[{'path':'main.n','text':MAIN}]})
 def test_only_an_exact_legacy_nc_root_is_archived(self):
  folder=self.ws.private_dir('native/main_12345678');(folder/'CMakeLists.txt').write_text('# Generated by Zénit from the current compiler configuration.\n# ncc compiler build-native\n',encoding='utf-8')
  atomic_json(folder.parent/'targets.json',{'main_12345678':'.lumen/native/main_12345678/CMakeLists.txt'})
  raw=ROOT_CMAKE.format(include='.lumen/native/targets.cmake').encode();(self.root/'CMakeLists.txt').write_bytes(raw)
  result=retire_legacy_cmake(self.ws,self.root);self.assertEqual(len(result),1);self.assertFalse((self.root/'CMakeLists.txt').exists())
  with zipfile.ZipFile(self.root/result[0]['backup']) as archive:self.assertEqual(archive.read('CMakeLists.txt'),raw)
  (self.root/'CMakeLists.txt').write_bytes(raw+b'# My custom target\n');self.assertEqual(retire_legacy_cmake(self.ws,self.root),[])
  (self.root/'CMakeLists.txt').write_bytes(raw);(folder/'CMakeLists.txt').write_text('# Generated by Zénit from the current compiler configuration.\n# gcc source.c\n')
  self.assertEqual(retire_legacy_cmake(self.ws,self.root),[]);self.assertTrue((self.root/'CMakeLists.txt').exists())
 def test_import_detection_ignores_comments_and_strings(self):
  self.assertEqual(imports('// use <project:wrong>;\nuse <io:output | project:one, two>;\nprintln("project:fake");'),['one','two'])
 def test_ncc_smoke_accepts_a_modular_entry(self):
  (self.root/'main.n').write_text(MAIN);(self.root/'helper.n').write_text(HELPER)
  task=self.app.features.tests.start(self.ws,{'framework':'ncc','consent':True})
  deadline=time.monotonic()+100
  while time.monotonic()<deadline:
   job=next(j for j in self.app.features.hilo.snapshot()['jobs'] if j['id']==task['job'])
   if job['state'] not in ('queued','running'):break
   time.sleep(.03)
  self.assertNotIn(job['state'],('queued','running'))
  run=self.app.features.tests.snapshot(self.ws,task['run'])['runs'][0]
  self.assertEqual(run['result']['summary']['passed'],1,run)
  self.assertEqual(run['result']['results'][0]['kind'],'smoke')

if __name__=='__main__':unittest.main()
