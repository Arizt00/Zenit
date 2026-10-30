import json,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.nc_refactor import verify
from tests.test_nc_project import MAIN,HELPER

ROOT=Path(__file__).resolve().parents[1]

class NcRefactorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.base=Path(self.temp.name);self.project=self.base/'Project with spaces';self.project.mkdir();(self.project/'main.n').write_text(MAIN);(self.project/'Helper.n').write_text(HELPER)
  self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.f=self.app.features;self.ws=self.app.workspace;self.ws.trusted=True;self.runtime=self.f.extension_runtime
  store=self.f.extensions;review=store.inspect_file(ROOT/'web/assets/extensions/nc-language-1.0.0-21v.zenit.7.vsix');store.install(review['ticket'],True)
  config=store.root/'.runtime-data/nc-lang.nc-language/configuration.json';config.parent.mkdir(parents=True,exist_ok=True);config.write_text(json.dumps({'nc.enableDiagnostics':False}),encoding='utf-8')
  self.runtime.start(self.ws,'nc-lang.nc-language',True)
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def rename(self,text=MAIN,path='main.n',name='result',at=None,buffers=None):
  from backend.nc_refactor import position
  at=text.index('answer') if at is None else at
  return self.runtime.request(self.ws,{'id':'nc-lang.nc-language','method':'provide','kind':'rename','document':{'path':path,'text':text,'language':'nc'},'position':position(text,at+1),'newName':name,'buffers':buffers or []})
 def test_public_module_function_and_its_callers_are_checked_without_writing_sources(self):
  result=self.rename();self.assertIn('refactor',result);changes=result['items'][0]['changes'];self.assertEqual(len(changes),2);self.assertEqual(result['refactor']['references'],2)
  self.assertEqual((self.project/'Helper.n').read_text(),HELPER);self.assertEqual((self.project/'main.n').read_text(),MAIN)
  self.assertTrue(verify(self.f,self.ws,{'id':result['refactor']['id'],'buffers':[]})['valid']);self.assertFalse((self.project/'src').exists());self.assertFalse(list(self.project.rglob('CMakeLists.txt')))
 def test_rename_from_declaration_reaches_multiple_importers_and_preserves_strings(self):
  second=MAIN.replace('app ::','second ::').replace('println(helper.worker.answer());','println("answer helper.worker.answer()"); /* helper.worker.answer() */ println(helper.worker.answer());')
  (self.project/'second.n').write_text(second);result=self.rename(HELPER,'Helper.n');self.assertEqual(len(result['items'][0]['changes']),3);self.assertEqual(result['refactor']['references'],3)
 def test_collision_and_invalid_current_project_return_no_edit(self):
  (self.project/'Helper.n').write_text(HELPER.replace('fa:', 'fn: public: result() -> int { return 0; } fa:'))
  with self.assertRaises(ValueError):self.rename()
  (self.project/'Helper.n').write_text(HELPER);(self.project/'main.n').write_text(MAIN.replace('answer()','missing()'))
  with self.assertRaisesRegex(ValueError,'NCC'):self.rename(HELPER,'Helper.n')
 def test_changed_unopened_dependency_invalidates_review(self):
  result=self.rename();(self.project/'Helper.n').write_text(HELPER.replace('42','43'))
  with self.assertRaisesRegex(ValueError,'cambiaron'):verify(self.f,self.ws,{'id':result['refactor']['id'],'buffers':[]})
 def test_ambiguous_modules_are_rejected_instead_of_partially_renamed(self):
  (self.project/'helper.n').write_text(HELPER) if not (self.project/'helper.n').exists() else None
  # A distinct location with the same canonical module is also ambiguous to
  # the current integration; it must never be silently edited.
  (self.project/'src').mkdir();(self.project/'src/helper.n').write_text(HELPER.replace('42','99'))
  with self.assertRaises(ValueError):self.rename()
 def test_pending_peer_buffer_is_checked_and_its_review_expires_after_edit(self):
  peer=HELPER.replace('42','43');result=self.rename(buffers=[{'path':'Helper.n','text':peer}]);identity=result['refactor']['id']
  self.assertTrue(verify(self.f,self.ws,{'id':identity,'buffers':[{'path':'Helper.n','text':peer}]})['valid'])
  with self.assertRaisesRegex(ValueError,'cambiaron'):verify(self.f,self.ws,{'id':identity,'buffers':[{'path':'Helper.n','text':HELPER}]})
  self.assertEqual((self.project/'Helper.n').read_text(),HELPER)
 def test_utf16_and_allman_declarations_keep_their_real_coordinates(self):
  from backend.nc_refactor import offset
  helper=HELPER.replace(' {','\n{');(self.project/'Helper.n').write_text(helper)
  text=MAIN.replace('println(helper','println("😀"); println(helper');result=self.rename(text)
  rows=result['items'][0]['changes'];edit=next(r for r in rows if r['uri'].endswith('/main.n'))['edits'][0]
  self.assertEqual(text[offset(text,edit['range']['start']):offset(text,edit['range']['end'])],'answer')
 def test_unchanged_name_is_an_empty_edit(self):self.assertEqual(self.rename(name='answer'),{'items':[]})
 def test_changed_machine_dependency_invalidates_review(self):
  dependency=self.project/'hardware.ncp';dependency.write_bytes(b'original');result=self.rename();dependency.write_bytes(b'modified')
  with self.assertRaisesRegex(ValueError,'cambiaron'):verify(self.f,self.ws,{'id':result['refactor']['id'],'buffers':[]})

if __name__=='__main__':unittest.main()
