import importlib.util,io,json,os,sys,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch

from backend.server import Application
from backend.runtime_paths import find_tool
from backend.extension_runtime import Host
from backend.preferences import atomic_json
from tests.test_hilo_tern import wait

ROOT=Path(__file__).resolve().parents[1]
NC='''use <io:output>;
vistaActual {
    stc:
        valor >> int <- 42;
    fn:
        run() -> bool {
            println(valor);
            return true;
        }
    ref main ->> run;
    fa:
        return true;
}
'''


class LanguageDepthFixture(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='zenit-language-depth-');self.root=Path(self.temp.name);self.project=self.root/'Project with spaces';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.root/'profile');self.f=self.app.features;self.ws=self.app.workspace;self.ws.trusted=True
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def source(self,name,text):
  p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
 def marker(self,name):self.source(name+'/CTestTestfile.cmake','# configured\n')


class LanguageDepthTests(LanguageDepthFixture):
 def test_rust_priming_is_lazy_unless_explicitly_configured(self):
  from backend.dependency_lsp import configure
  profile={'argv':['rust-analyzer'],'languages':['rust']}
  self.assertFalse(configure(profile,self.ws)['initializationOptions']['cachePriming']['enable'])
  self.assertNotIn('initializationOptions',profile)
  for options in ({'cachePriming':{'enable':True}},{'cachePriming.enable':True}):
   profile['initializationOptions']=options
   result=configure(profile,self.ws)
   self.assertEqual(result['initializationOptions'],options)
   self.assertTrue(result['settings']['rust-analyzer']['cachePriming']['enable'])
  profile['settings']={'rust-analyzer':{'cachePriming':{'enable':True}}}
  self.assertTrue(configure(profile,self.ws)['settings']['rust-analyzer']['cachePriming']['enable'])
 def test_rust_probe_uses_an_interior_utf16_position_and_restores_the_real_crate_entry(self):
  from backend.language_verification import LanguageVerification
  import re,threading
  original='fn main() { println!("original"); }\n';entry=self.source('src/main.rs',original);records=[]
  class Session:
   def __init__(self,*args):self.text='';self.uri=entry.as_uri();self.stderr=''
   def notify(self,method,params):self.text=params['textDocument']['text']
   def request(self,method,params,**kwargs):
    column=params['position']['character'];assert any(m.start()<column<m.end() for m in re.finditer(r'\bvalue\b',self.text))
    span=lambda m:{'start':{'line':0,'character':m.start()},'end':{'line':0,'character':m.end()}}
    hits=list(re.finditer(r'\bvalue\b',self.text))
    return [{'uri':self.uri,'range':span(hits[0])}] if method.endswith('/definition') else {'changes':{self.uri:[{'range':span(m),'newText':'verified_value'} for m in hits]}}
   def close(self):pass
  with patch('backend.lsp.LanguageSession',Session),patch('backend.language_verification.find_tool',return_value='rust-analyzer'):
   LanguageVerification(self.f).semantic(self.f,self.ws,'rust',entry,original,lambda *args:records.append(args),threading.Event())
  self.assertEqual([r[1] for r in records],['passed','passed']);self.assertEqual(entry.read_text(),original)
 def test_ctest_finds_generated_nested_kit_without_duplicate_subdirectory_suites(self):
  self.source('kit/CMakeLists.txt','project(fixture)');self.marker('kit/build/c/main-1234');self.marker('kit/build/c/main-1234/tests');data=self.f.tests.discover(self.ws)
  self.assertEqual(data['ctestDirectories'],['kit/build/c/main-1234']);self.assertIn('ctest',[x['id'] for x in data['frameworks']]);plan=self.f.tests.plan(self.ws,{'framework':'ctest','build':True});self.assertIn(str(self.project/'kit/build/c/main-1234'),plan['commands'][0])
 def test_ctest_requires_explicit_current_directory_for_multiple_targets(self):
  self.marker('build/c/one');self.marker('build/cpp/two')
  with self.assertRaisesRegex(ValueError,'Selecciona'):self.f.tests.plan(self.ws,{'framework':'ctest'})
  plan=self.f.tests.plan(self.ws,{'framework':'ctest','directory':'build/cpp/two'});self.assertIn(str(self.project/'build/cpp/two'),plan['commands'][0])
  with self.assertRaises(ValueError):self.f.tests.plan(self.ws,{'framework':'ctest','directory':'../outside'})
 def test_ctest_discovery_invalidates_after_new_build_directory(self):
  self.assertNotIn('ctest',[x['id'] for x in self.f.tests.discover(self.ws)['frameworks']]);self.marker('build/c/one');self.assertEqual(self.f.tests.discover(self.ws)['ctestDirectories'],['build/c/one'])
 def test_cargo_tests_use_the_selected_compiler_instead_of_an_unconfigured_rustup_proxy(self):
  self.source('Cargo.toml','[package]\nname="fixture"\nversion="0.1.0"');rust=find_tool('rustc');plan=self.f.tests.plan(self.ws,{'framework':'cargo'})
  for command in plan['commands']:self.assertIn('build.rustc='+json.dumps(rust),command)
 @unittest.skipUnless(os.name=='nt','Windows rustup layout')
 def test_rust_analyzer_prefers_the_real_toolchain_and_respects_explicit_override(self):
  toolchain=self.root/'rustup/toolchains/stable-x86_64-pc-windows-msvc/bin';toolchain.mkdir(parents=True);binary=toolchain/'rust-analyzer.exe';binary.touch();explicit=self.root/'chosen.exe';explicit.touch()
  with patch.dict(os.environ,{'RUSTUP_HOME':str(self.root/'rustup')}),patch('backend.foundation.bundled_tool',return_value=None),patch('backend.runtime_paths.shutil.which',return_value='rustup-proxy'):
   self.assertEqual(find_tool('rust-analyzer'),str(binary));self.assertEqual(find_tool('rust-analyzer',{'rust-analyzer':str(explicit)}),str(explicit))
 def test_nc_discovery_masks_comments_and_requires_a_selected_entry(self):
  self.source('one.n',NC);self.source('two.n',NC.replace('vistaActual','another'));self.source('comment.n','/*\n ref main ->> fake;\n*/\n');inventory=self.f.tests.discover(self.ws)
  entries=[x for x in inventory['tests'] if x['framework']=='ncc'];self.assertEqual(len(entries),2);self.assertTrue(all(x['kind']=='smoke' for x in entries));self.assertEqual(entries[0]['line'],10)
  with self.assertRaisesRegex(ValueError,'Selecciona'):self.f.tests.plan(self.ws,{'framework':'ncc'})
  plan=self.f.tests.plan(self.ws,{'framework':'ncc','selection':'one.n::main'});self.assertIn('prueba de humo',plan['note']);self.assertEqual(plan['commands'][0][-2:],['--source','one.n'])
 @unittest.skipUnless(find_tool('node'),'Node unavailable')
 def test_workspace_edit_change_event_has_a_complete_utf16_range(self):
  before='first\r\n😀 last';self.source('event.txt',before);archive=io.BytesIO()
  code='''const v=require('vscode');exports.activate=c=>{let changes=[];v.workspace.onDidChangeTextDocument(e=>{changes.push(...e.contentChanges.map(c=>({range:c.range,length:c.rangeLength})));});v.commands.registerCommand('fixture.edit',async()=>{const d=await v.workspace.openTextDocument(v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,'event.txt'));const e=new v.WorkspaceEdit();e.replace(d.uri,new v.Range(0,0,1,7),'after');await v.workspace.applyEdit(e);return changes;});};'''
  with zipfile.ZipFile(archive,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'event-range','version':'1.0.0','engines':{'vscode':'*'},'main':'main.js'}));z.writestr('extension/main.js',code)
  review=self.f.extensions.inspect_bytes(archive.getvalue());self.f.extensions.install(review['ticket'],True);runtime=self.f.extension_runtime;runtime.start(self.ws,'qa.event-range',True);result=runtime.request(self.ws,{'id':'qa.event-range','method':'command','command':'fixture.edit'})['result'];self.assertEqual(len(result),1);self.assertEqual(result[0]['range']['end'],{'line':1,'character':7});self.assertEqual(result[0]['length'],len(before.encode('utf-16-le'))//2)
 @unittest.skipUnless(find_tool('ncc'),'NCC unavailable')
 def test_nc_smoke_reports_a_real_type_error_and_marks_result_stale_after_edit(self):
  self.source('main.n',NC);tests=self.f.tests
  run=tests.start(self.ws,{'framework':'ncc','consent':True});wait(self.f.hilo,run['job'],timeout=150);result=tests.snapshot(self.ws,run['run'])['runs'][0];self.assertEqual(result['result']['summary']['passed'],1);self.assertEqual(result['result']['results'][0]['kind'],'smoke')
  self.source('main.n',NC.replace('valor >> int <- 42','valor >> int <- "text"'));self.assertTrue(tests.snapshot(self.ws,run['run'])['runs'][0]['stale'])
  failed=tests.start(self.ws,{'framework':'ncc','consent':True});wait(self.f.hilo,failed['job'],timeout=150);result=tests.snapshot(self.ws,failed['run'])['runs'][0];self.assertEqual(result['state'],'failed');self.assertEqual(result['result']['summary']['failed'],1);self.assertEqual(result['result']['results'][0]['path'],'main.n')


@unittest.skipUnless(find_tool('node') and find_tool('ncc'),'nC extension prerequisites unavailable')
class NcProviderDepthTests(LanguageDepthFixture):
 def setUp(self):
  super().setUp();package=self.root/'package'
  with zipfile.ZipFile(ROOT/'web/assets/extensions/nc-language-1.0.0-21v.vsix') as archive:archive.extractall(package)
  self.package=package/'extension';spec=importlib.util.spec_from_file_location('nc_scope_patch',ROOT/'integrations/nc-language/scoped-navigation.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);source=self.package/'src/extension.js';source.write_text(module.patch(source.read_text()),encoding='utf-8');(self.package/'src/zenit-scoped-navigation.cjs').write_bytes((ROOT/'integrations/nc-language/scoped-navigation.cjs').read_bytes())
  storage=self.root/'storage';storage.mkdir();atomic_json(storage/'configuration.json',{'nc.nccPath':find_tool('ncc'),'nc.enableDiagnostics':False});manifest=json.loads((self.package/'package.json').read_text());self.host=Host(find_tool('node'),self.package,self.package/manifest['main'],self.ws,{'extensionId':'nc-lang.nc-language','manifest':manifest,'storage':str(storage),'locale':'es','extensions':[]})
 def tearDown(self):self.host.close();super().tearDown()
 def provide(self,kind,text,at=None,name='nuevoValor'):
  self.source('scopes.n','// saved bytes stay untouched\n');offset=text.rfind('valor') if at is None else at;before=text[:offset];position={'line':before.count('\n'),'character':len(before.rsplit('\n',1)[-1].encode('utf-16-le'))//2+1};return self.host.request({'method':'provide','kind':kind,'document':{'path':str(self.project/'scopes.n'),'text':text,'language':'nc'},'position':position,'newName':name})['items']
 def test_two_containers_definition_references_rename_and_outline_are_separate(self):
  text=NC+'\n'+NC.replace('vistaActual','otraVista');items=self.provide('definition',text);self.assertEqual(items[0]['range']['start']['line'],17)
  references=self.provide('references',text);self.assertEqual([r['range']['start']['line'] for r in references],[17,20])
  changes=self.provide('rename',text)[0]['changes'][0]['edits'];self.assertEqual([r['range']['start']['line'] for r in changes],[17,20]);self.assertEqual((self.project/'scopes.n').read_text(),'// saved bytes stay untouched\n')
  outline=self.provide('symbols',text);self.assertEqual(len(outline),2);self.assertTrue(all(len(row['children'])==2 for row in outline));self.assertEqual(outline[0]['range']['end']['line'],12)
 def test_local_parameter_shadows_field_and_never_renames_an_unrelated_file(self):
  text=NC.replace('run() -> bool','run(valor >> int) -> bool');self.source('other.n',NC)
  items=self.provide('rename',text)[0]['changes'];self.assertEqual(len(items),1);self.assertEqual([r['range']['start']['line'] for r in items[0]['edits']],[5,6]);self.assertEqual(self.provide('definition',text)[0]['range']['start']['line'],5)
 def test_collision_and_broken_scopes_produce_no_workspace_edit(self):
  text=NC.replace('valor >> int <- 42;','valor >> int <- 42;\n        nuevoValor >> int <- 1;')
  self.assertEqual(self.provide('rename',text),[]);self.assertRegex(self.host.logs,'nombre|símbolo')
  self.assertEqual(self.provide('rename',NC[:-2]),[]);self.assertIn('llaves',self.host.logs)
 def test_comments_strings_and_qualified_members_are_not_renamed(self):
  text=NC.replace('println(valor);','// valor { }\n            println("😀 valor");\n            object.valor;\n            println(valor);')
  edits=self.provide('rename',text)[0]['changes'][0]['edits'];self.assertEqual(len(edits),2);self.assertEqual(edits[0]['range']['start']['line'],3);self.assertEqual(edits[1]['range']['start']['line'],9)
 def test_utf16_columns_after_an_emoji_stay_exact(self):
  text=NC.replace('println(valor);','println("😀"); println(valor);');edits=self.provide('rename',text)[0]['changes'][0]['edits'];line=text.splitlines()[6];column=len(line[:line.index('valor')].encode('utf-16-le'))//2;self.assertEqual(edits[1]['range']['start'],{'line':6,'character':column})
 def test_new_name_cannot_capture_an_outer_visible_binding(self):
  text=NC.replace('run() -> bool','run(nuevoValor >> int) -> bool')
  self.assertEqual(self.provide('rename',text),[]);self.assertRegex(self.host.logs,'nombre|símbolo')
 def test_qualified_members_resolve_their_container_and_rename_only_that_binding(self):
  text=NC+'\n'+NC.replace('vistaActual','otraVista').replace('println(valor);','println(vistaActual.valor); println(valor);')
  at=text.index('valor',text.index('vistaActual.valor'))
  location=self.provide('definition',text,at=at)[0];self.assertEqual(location['range']['start']['line'],3)
  edits=self.provide('rename',text,at=at)[0]['changes'][0]['edits']
  self.assertEqual([row['range']['start']['line'] for row in edits],[3,6,20])
 def test_project_member_definition_goes_to_the_actual_module(self):
  self.source('Helper.n',NC)
  text='use <project:helper>;\n'+NC.replace('println(valor);','helper.vistaActual.run();')
  items=self.provide('definition',text,at=text.index('run();'))
  self.assertEqual(Path(items[0]['uri']['fsPath']),self.project/'Helper.n')
  self.assertEqual(items[0]['range']['start']['line'],5)


class NativeBridgeDepthTests(LanguageDepthFixture):
 def setUp(self):
  super().setUp();self.source('main.py','from helper import value\nprint(value)\n');self.source('helper.py','value = 7\n')
  from backend.extension_lsp import NativeLanguageHost
  self.host=NativeLanguageHost(self.ws,{'argv':[sys.executable,str(ROOT/'tests/fixtures/lsp_depth.py')]},'python','Protocol fixture')
 def tearDown(self):self.host.close();super().tearDown()
 def request(self,kind,**extra):
  return self.host.request({'method':'provide','kind':kind,'document':{'path':'main.py','text':'from helper import value\nprint(value)\n','language':'python'},'position':{'line':1,'character':8},'range':{'start':{'line':0,'character':0},'end':{'line':1,'character':12}},**extra})
 def test_announced_native_rename_is_exposed_and_keeps_both_files_for_review(self):
  self.assertIn('rename',[p['kind'] for p in self.host.capabilities['providers']]);edit=self.request('rename',newName='count')['items'][0];self.assertEqual(len(edit['changes']),2);self.assertTrue(all(e['newText']=='count' for c in edit['changes'] for e in c['edits']));self.assertEqual((self.project/'helper.py').read_text(),'value = 7\n')
 def test_native_refactoring_is_exposed_without_writing_the_project(self):
  self.assertIn('actions',[p['kind'] for p in self.host.capabilities['providers']]);actions=self.request('actions')['items'];self.assertEqual(actions[0]['kind'],'refactor.rewrite');self.assertEqual(actions[0]['edit']['changes'][0]['edits'][0]['newText'],'8');self.assertEqual((self.project/'helper.py').read_text(),'value = 7\n')
 def test_versioned_or_resource_edits_cannot_silently_lose_guards(self):
  self.request('definition');uri=(self.project/'main.py').as_uri()
  with self.assertRaisesRegex(ValueError,'cambió'):self.host.workspace_edit({'documentChanges':[{'textDocument':{'uri':uri,'version':0},'edits':[]}]})
  with self.assertRaisesRegex(ValueError,'recursos'):self.host.workspace_edit({'documentChanges':[{'kind':'rename','oldUri':uri,'newUri':uri+'new'}]})
  with self.assertRaises(PermissionError):self.host.workspace_edit({'changes':{(self.root/'outside.py').as_uri():[]}})


if __name__=='__main__':unittest.main()
