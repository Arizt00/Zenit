import json,sys,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.project_console import dispatch
from tests.test_hilo_tern import wait

ROOT=Path(__file__).resolve().parents[1]

class ExperienceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.ws=self.app.workspace;self.ws.trusted=True;self.f=self.app.features
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def source(self,name,text):p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p
 def job(self,result,timeout=20):
  job=self.app.runner.jobs[result['job']];end=time.monotonic()+timeout
  while not job.done and time.monotonic()<end:time.sleep(.02)
  self.assertTrue(job.done,job.output);return job
 def test_runner_prepared_input_eof_and_raw_output(self):
  result=self.app.runner.start([[sys.executable,'-u','-c','import sys; print("recibido:"+sys.stdin.read(),end="")']],self.project,stdin='hola 🪐\n',close_stdin=True)
  job=self.job(result);self.assertEqual(job.code,0);self.assertEqual(job.stream_output.replace('\r\n','\n'),'recibido:hola 🪐\n');self.assertGreater(job.elapsed,0);self.assertIn('Process exited',job.output)
 def test_console_uses_runtime_for_quoted_paths_arguments_build_and_check(self):
  file=self.source('sub dir/echo.py','import sys\nprint("|".join(sys.argv[1:]))\n')
  result=dispatch(self.f,self.ws,{'command':'run "echo.py" -- "dos palabras" tres','cwd':'sub dir'});job=self.job(result)
  self.assertEqual(job.code,0,job.output);self.assertEqual(job.stream_output.strip(),'dos palabras|tres');self.assertEqual(result['path'],'sub dir/echo.py')
  result=dispatch(self.f,self.ws,{'command':'build "sub dir/echo.py"'});job=self.job(result);self.assertEqual(job.code,0,job.output);self.assertNotIn('dos palabras',job.output)
  self.assertIn('output',dispatch(self.f,self.ws,{'command':'check "sub dir/echo.py"'}))
  with self.assertRaises(PermissionError):dispatch(self.f,self.ws,{'command':'run ../outside.py'})
  self.assertIn('0.5.5',dispatch(self.f,self.ws,{'command':'version'})['output'])
 def test_console_eof_unblocks_running_program(self):
  self.source('read.py','import sys\nprint(len(sys.stdin.read()))\n')
  run=dispatch(self.f,self.ws,{'command':'run read.py'});job=self.app.runner.jobs[run['job']];end=time.monotonic()+10
  while not job.process and time.monotonic()<end:time.sleep(.02)
  job.write('abc');job.finish_input();job=self.job(run);self.assertEqual(job.code,0);self.assertEqual(job.stream_output.strip(),'3')
 def test_console_runs_each_installed_primary_language_with_its_runtime(self):
  flow=self.f.workflows;passed=[]
  for kit in flow.catalog(self.ws)['kits']:
   with self.subTest(language=kit['id']):
    self.assertTrue(kit['ready'],kit['id'])
    plan=flow.scaffold_plan(self.ws,{'language':kit['id'],'folder':'kit-'+kit['id']});created=flow.scaffold(self.ws,{'plan':plan['id']})
    if created.get('task'):
     self.assertEqual(self.job(created['task'],60).code,0);files=list((self.project/created['folder']).rglob('*.n'))+list((self.project/created['folder']).rglob('*.nc'));entry=files[0].relative_to(self.project).as_posix()
    else:entry=created['entry']
    run=dispatch(self.f,self.ws,{'command':'run "'+entry+'"'});job=self.job(run,60);self.assertEqual(job.code,0,job.output)
    self.assertEqual(run['language'],kit['id']);passed.append(kit['id'])
  self.assertEqual(set(passed),{'python','c','cpp','java','asm','rust','nc'})
 def test_queued_cancellation_finishes_without_waiting_for_busy_workers(self):
  blockers=[self.app.runner.start([[sys.executable,'-u','-c','import time;time.sleep(60)']],self.project) for _ in range(self.app.runner.parallelism)]
  end=time.monotonic()+10
  while not all(self.app.runner.jobs[x['job']].process for x in blockers) and time.monotonic()<end:time.sleep(.02)
  queued=self.app.runner.start([[sys.executable,'-c','print("must not execute")']],self.project);job=self.app.runner.jobs[queued['job']];self.assertTrue(job.queued);job.cancel();self.assertTrue(job.done);self.assertIsNone(job.process)
  for run in blockers:self.app.runner.jobs[run['job']].cancel()
 def test_countercheck_executes_both_snapshots_sequentially_and_keeps_sources(self):
  saved='value=int(input())\nprint(value+1)\n';buffer='value=int(input())\nprint(value+2)\n';file=self.source('main.py',saved)
  plan=self.f.countercheck.plan(self.ws,{'path':'main.py','content':buffer,'stdin':'4\n','timeout':5});task=self.f.countercheck.run(self.ws,{'plan':plan['id']})
  self.assertEqual(task,self.f.countercheck.run(self.ws,{'plan':plan['id']}));result=wait(self.f.hilo,task['job'])
  self.assertEqual(result['state'],'done',result);report=result['result'];self.assertFalse(report['equivalent']);self.assertEqual([r['output'].strip() for r in report['results']],['5','6']);self.assertEqual(file.read_text(),saved);self.assertNotEqual(report['savedSha256'],report['bufferSha256'])
  self.assertEqual(task,self.f.countercheck.run(self.ws,{'plan':plan['id']}))
 def test_countercheck_rejects_changed_disk_and_cancels_infinite_program(self):
  file=self.source('main.py','while True: pass\n');plan=self.f.countercheck.plan(self.ws,{'path':'main.py','content':'print(42)\n','timeout':10})
  task=self.f.countercheck.run(self.ws,{'plan':plan['id']});end=time.monotonic()+10
  while not any(j.process for j in self.app.runner.jobs.values()) and time.monotonic()<end:time.sleep(.02)
  self.f.hilo.cancel(task['job']);result=wait(self.f.hilo,task['job']);self.assertEqual(result['state'],'cancelled');self.assertEqual(len(self.app.runner.jobs),1)
  plan=self.f.countercheck.plan(self.ws,{'path':'main.py','content':'print(42)'});file.write_text('print(1)')
  with self.assertRaises(ValueError):self.f.countercheck.run(self.ws,{'plan':plan['id']})
 def test_countercheck_compares_full_output_even_when_displayed_tails_match(self):
  self.source('main.py','print("saved"+"x"*20000)\n');plan=self.f.countercheck.plan(self.ws,{'path':'main.py','content':'print("buffer"+"x"*20000)\n','timeout':5})
  task=self.f.countercheck.run(self.ws,{'plan':plan['id']});state=wait(self.f.hilo,task['job']);self.assertEqual(state['state'],'done',state)
  report=state['result'];a,b=report['results'];self.assertEqual(a['output'],b['output']);self.assertTrue(a['outputComplete']);self.assertTrue(a['outputTruncated']);self.assertGreater(a['outputBytes'],16000);self.assertNotEqual(a['outputSha256'],b['outputSha256']);self.assertFalse(report['equivalent'])
 def test_lantern_replay_and_contract_survive_revisions_and_reopen(self):
  path='main.py';text='print("Hello "+input())\n';file=self.source(path,text);options={'inputEnabled':True,'stdin':'Ada\n','closeInput':True,'verifyEnabled':True,'expectedExit':0,'match':'exact','expectedOutput':'Hello Ada\n','timeout':5}
  self.f.lantern.configure(self.ws,{'path':path,'options':options});self.f.lantern.start(self.ws,path,text,1)
  def completed(version):
   end=time.monotonic()+15
   while time.monotonic()<end:
    state=self.f.lantern.snapshot()
    if state.get('bufferVersion')==version and state['verification']['status'] in ('passed','failed'):return state
    time.sleep(.04)
   self.fail(str(state))
  state=completed(1);self.assertEqual(state['verification']['status'],'passed',state)
  self.f.lantern.buffer(self.ws,path,'print("Bye "+input())\n',2);state=completed(2);self.assertEqual(state['verification']['status'],'failed');self.assertEqual(state['code'],0)
  self.assertEqual(file.read_text(),text);self.f.lantern.stop();self.assertEqual(self.f.lantern.get_options(self.ws,path),options)
  self.assertEqual(self.f.lantern.snapshot()['history'][-1]['verification']['status'],'failed')
 def test_invalid_options_and_untrusted_execution_are_rejected(self):
  self.source('main.py','print(1)')
  for options in ({'stdin':'x'*20000},{'timeout':-1},{'expectedExit':True},{'match':'regex'}):
   with self.assertRaises(ValueError):self.f.lantern.configure(self.ws,{'path':'main.py','options':options})
  self.ws.trusted=False
  with self.assertRaises(PermissionError):self.f.countercheck.plan(self.ws,{'path':'main.py','content':'print(1)'})
  with self.assertRaises(PermissionError):dispatch(self.f,self.ws,{'command':'run main.py'})

if __name__=='__main__':unittest.main()
