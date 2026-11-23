import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]
class FileRenameTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.project=self.base/'project';self.project.mkdir()
  self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.f=self.app.features;self.ws=self.app.workspace;self.ws.trusted=True
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def rename(self,path,destination):return self.f.post('/files/operation',{'operation':'rename','path':path,'destination':destination})
 def file(self,name,content=b'original\r\n'):
  file=self.project/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(content);return file
 def test_rename_preserves_bytes_drafts_recovery_and_emits_resource_event(self):
  self.file('src/main.py');self.f.buffers.update(self.ws,{'path':'src/main.py','text':'unsaved','sequence':0,'saved':False})
  self.f.workbenches.checkpoint(self.ws,{'session':{'documents':[{'path':'src/main.py','dirty':True,'content':'unsaved'}],'active':'src/main.py'}})
  with patch.object(self.f.extension_services,'emit') as emit:result=self.rename('src','source')
  self.assertEqual(result['path'],'source');self.assertFalse((self.project/'src').exists());self.assertEqual((self.project/'source/main.py').read_bytes(),b'original\r\n')
  self.assertEqual(self.f.buffers.items['source/main.py']['text'],'unsaved');self.assertEqual(self.f.workbenches.snapshot(self.ws)['session']['active'],'source/main.py')
  self.assertTrue(any(call.args[0]=='zenit.workspace.edit' for call in emit.call_args_list))
 def test_collision_and_traversal_never_overwrite_or_move_the_source(self):
  self.file('main.py',b'one');self.file('other.py',b'two')
  for destination in ('other.py','../outside.py','.lumen/hidden.py'):
   with self.assertRaises((ValueError,PermissionError)):self.rename('main.py',destination)
  self.assertEqual((self.project/'main.py').read_bytes(),b'one');self.assertEqual((self.project/'other.py').read_bytes(),b'two')
 def test_case_only_name_and_extension_change_are_real_renames(self):
  self.file('Main.py');self.rename('Main.py','main.py');self.assertIn('main.py',[p.name for p in self.project.iterdir()]);self.assertNotIn('Main.py',[p.name for p in self.project.iterdir()])
  self.rename('main.py','main.txt');self.assertEqual((self.project/'main.txt').read_bytes(),b'original\r\n')
 def test_active_lantern_is_checked_before_the_disk_operation(self):
  self.file('main.py')
  with patch.object(self.f.lantern,'snapshot',return_value={'active':True,'path':'main.py'}):
   with self.assertRaisesRegex(ValueError,'Lantern'):self.rename('main.py','next.py')
  self.assertTrue((self.project/'main.py').exists());self.assertFalse((self.project/'next.py').exists())
 def test_delete_folder_uses_recoverable_trash_and_removes_session_entries(self):
  self.file('folder/a.bin',bytes(range(256)));self.file('keep.txt')
  self.f.buffers.update(self.ws,{'path':'folder/a.txt','text':'saved','sequence':0,'saved':True});self.file('folder/a.txt',b'saved')
  self.f.workbenches.checkpoint(self.ws,{'session':{'documents':[{'path':'folder/a.txt'},{'path':'keep.txt'}],'active':'folder/a.txt','tabGroups':[{'id':'g','name':'group','paths':['folder/a.txt']}],'activeTabGroup':'g'}})
  result=self.f.post('/files/operation',{'operation':'delete','path':'folder'});self.assertFalse((self.project/'folder').exists());self.assertNotIn('folder/a.txt',self.f.buffers.items)
  session=self.f.workbenches.snapshot(self.ws)['session'];self.assertEqual(session['active'],'keep.txt');self.assertEqual(session['tabGroups'],[])
  self.f.post('/files/operation',{'operation':'restore','ticket':result['ticket']});self.assertEqual((self.project/'folder/a.bin').read_bytes(),bytes(range(256)))
 def test_delete_refuses_an_unsaved_shared_draft_and_restore_never_overwrites(self):
  self.file('main.py',b'original');self.f.buffers.update(self.ws,{'path':'main.py','text':'draft','sequence':0,'saved':False})
  with self.assertRaisesRegex(ValueError,'sin guardar'):self.f.post('/files/operation',{'operation':'delete','path':'main.py'})
  self.assertEqual((self.project/'main.py').read_bytes(),b'original')
  self.f.buffers.clear();deleted=self.f.post('/files/operation',{'operation':'delete','path':'main.py'});self.file('main.py',b'new file')
  with self.assertRaises(ValueError):self.f.post('/files/operation',{'operation':'restore','ticket':deleted['ticket']})
  self.assertEqual((self.project/'main.py').read_bytes(),b'new file');self.assertEqual((self.project/'.lumen/trash'/deleted['ticket']/'content').read_bytes(),b'original')
 @unittest.skipUnless(os.name=='nt','Windows naming rules')
 def test_windows_reserved_or_trailing_names_are_explained(self):
  self.file('main.py')
  for name in ('CON.txt','name.','name '):
   with self.assertRaises(ValueError):self.rename('main.py',name)

if __name__=='__main__':unittest.main()
