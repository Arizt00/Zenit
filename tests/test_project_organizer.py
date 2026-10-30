import json,sys,tempfile,threading,time,unittest,subprocess
from concurrent.futures import CancelledError
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
ROOT=Path(__file__).resolve().parents[1]

class ProjectOrganizerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir()
  self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.ws=self.app.workspace;self.ws.trusted=True;self.f=self.app.features;self.org=self.f.organizer
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def file(self,path,text='data'):
  p=self.project/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
 def plan(self,paths,destination='',**extra):return self.org.plan(self.ws,dict(paths=paths,destination=destination,**extra))
 def commit(self,plan,event=None):return self.org.commit(self.ws,self.org.plans[plan['id']],event or threading.Event())
 def test_batch_moves_and_merges_keep_both_without_overwriting(self):
  self.file('a/shared/one.c','one');self.file('b/shared/two.c','two');self.file('b/existing.c','source');self.file('target/existing.c','target')
  conflict=self.plan(['a','b'],'target',mode='merge');self.assertIn('target/existing.c',conflict['conflicts'])
  with self.assertRaises(ValueError):self.org.apply(self.ws,{'plan':conflict['id']})
  self.assertTrue((self.project/'a/shared/one.c').is_file())
  plan=self.plan(['a','b'],'target',mode='merge',conflicts='keep-both');result=self.commit(plan)
  self.assertEqual((self.project/'target/existing.c').read_text(),'target');self.assertEqual((self.project/'target/existing (2).c').read_text(),'source')
  self.assertEqual((self.project/'target/shared/two.c').read_text(),'two');self.assertEqual((self.project/'target/shared/one.c').read_text(),'one')
  self.assertFalse((self.project/'a').exists());self.assertFalse((self.project/'b').exists());self.assertEqual(result['foldersMerged'],3)
 def test_can_extract_files_to_project_root_and_deduplicate_nested_selection(self):
  self.file('a/x.py','print(42)');self.file('a/y.py')
  plan=self.plan(['a/x.py']);self.commit(plan);self.assertTrue((self.project/'x.py').is_file())
  (self.project/'target').mkdir();plan=self.plan(['a','a/y.py'],'target');self.assertEqual(len(plan['moves']),1);self.commit(plan)
  self.assertTrue((self.project/'target/a/y.py').is_file())
 def test_stale_review_and_path_cycles_are_rejected(self):
  source=self.file('a/file.c');(self.project/'target').mkdir();plan=self.plan(['a'],'target');source.write_text('different bytes')
  with self.assertRaisesRegex(ValueError,'cambiaron'):self.commit(plan)
  with self.assertRaises(ValueError):self.plan(['a'],'a')
  with self.assertRaises((ValueError,PermissionError)):self.plan(['../outside'])
  (self.project/'.lumen').mkdir(exist_ok=True)
  with self.assertRaises(ValueError):self.plan(['.lumen'])
 def test_cancel_and_second_rename_failure_roll_back_first_move(self):
  self.file('a.c','A');self.file('b.c','B');(self.project/'target').mkdir();plan=self.plan(['a.c','b.c'],'target');event=threading.Event()
  with patch.object(self.f.hilo,'report',side_effect=lambda *_:event.set()):
   with self.assertRaises(CancelledError):self.commit(plan,event)
  self.assertEqual((self.project/'a.c').read_text(),'A');self.assertFalse((self.project/'target/a.c').exists())
  plan=self.plan(['a.c','b.c'],'target');original=Path.rename
  def rename(source,to):
   if source==self.project/'b.c':raise PermissionError('locked file')
   return original(source,to)
  with patch.object(Path,'rename',rename):
   with self.assertRaises(PermissionError):self.commit(plan)
  self.assertEqual((self.project/'a.c').read_text(),'A');self.assertEqual((self.project/'b.c').read_text(),'B')
 def test_manual_order_persists_outside_project(self):
  self.file('z.c');self.file('a.c');self.org.layout(self.ws,{'orders':{'':['z.c','a.c']}})
  self.assertEqual(self.org.layout(self.ws)['orders'][''],['z.c','a.c'])
  with self.assertRaises(ValueError):self.org.layout(self.ws,{'orders':{'':['sub/other.c']}})
  self.assertFalse((self.project/'explorer.json').exists())
 def test_undo_move_preserves_later_content_edits_and_dirty_recovery(self):
  self.file('a/main.py','disk');(self.project/'target').mkdir()
  self.f.buffers.update(self.ws,{'path':'a/main.py','text':'unsaved','sequence':0,'saved':False})
  moved=self.commit(self.plan(['a/main.py'],'target'));receipt=self.org.receipts[moved['undoReceipt']]
  (self.project/'target/main.py').write_text('edited after moving')
  result=self.org.revert(self.ws,receipt,threading.Event())
  self.assertTrue(result['undone']);self.assertEqual((self.project/'a/main.py').read_text(),'edited after moving')
  self.assertEqual(self.f.buffers.items['a/main.py']['text'],'unsaved');self.assertFalse((self.project/'target/main.py').exists())
 def test_undo_merge_rebuilds_removed_folders_and_preserves_unrelated_target_files(self):
  self.file('a/shared/one.c','one');self.file('b/shared/two.c','two');self.file('target/unrelated.c','keep')
  moved=self.commit(self.plan(['a','b'],'target',mode='merge'));receipt=self.org.receipts[moved['undoReceipt']]
  self.org.revert(self.ws,receipt,threading.Event())
  self.assertEqual((self.project/'a/shared/one.c').read_text(),'one');self.assertEqual((self.project/'b/shared/two.c').read_text(),'two')
  self.assertEqual((self.project/'target/unrelated.c').read_text(),'keep');self.assertFalse((self.project/'target/shared').exists())
 def test_undo_rejects_occupied_original_paths_and_replaced_moved_files(self):
  self.file('main.py','original');(self.project/'target').mkdir();moved=self.commit(self.plan(['main.py'],'target'));receipt=self.org.receipts[moved['undoReceipt']]
  self.file('main.py','new original path')
  with self.assertRaisesRegex(ValueError,'ocupada'):self.org.revert(self.ws,receipt,threading.Event())
  self.assertEqual((self.project/'main.py').read_text(),'new original path');self.assertEqual((self.project/'target/main.py').read_text(),'original')
  (self.project/'main.py').unlink();replacement=self.file('replacement.py','replacement');replacement.replace(self.project/'target/main.py')
  with self.assertRaisesRegex(ValueError,'sustituido'):self.org.revert(self.ws,receipt,threading.Event())
  self.assertEqual((self.project/'target/main.py').read_text(),'replacement')
 def test_cancelled_undo_rolls_back_the_whole_batch(self):
  self.file('a.py','A');self.file('b.py','B');(self.project/'target').mkdir();moved=self.commit(self.plan(['a.py','b.py'],'target'));receipt=self.org.receipts[moved['undoReceipt']];event=threading.Event()
  with patch.object(self.f.hilo,'report',side_effect=lambda *_:event.set()):
   with self.assertRaises(CancelledError):self.org.revert(self.ws,receipt,event)
  self.assertEqual((self.project/'target/a.py').read_text(),'A');self.assertEqual((self.project/'target/b.py').read_text(),'B')
  self.assertFalse((self.project/'a.py').exists());self.assertFalse(receipt['undone'])
 def test_move_preserves_shared_dirty_buffers_recovery_and_virtual_groups(self):
  self.file('a.c','disk');self.file('b.c');(self.project/'target').mkdir()
  self.f.buffers.update(self.ws,{'path':'a.c','text':'unsaved','sequence':0,'saved':False})
  self.f.workbenches.checkpoint(self.ws,{'session':{'documents':[{'path':'a.c','dirty':True,'content':'unsaved'},{'path':'b.c'}],'active':'a.c','tabGroups':[{'id':'g','name':'Module','paths':['a.c','b.c']}],'activeTabGroup':'g'}})
  self.commit(self.plan(['a.c'],'target'))
  recovered=self.f.workbenches.snapshot(self.ws)['session'];self.assertEqual(recovered['active'],'target/a.c');self.assertEqual(recovered['documents'][0]['content'],'unsaved');self.assertEqual(recovered['tabGroups'][0]['paths'],['target/a.c','b.c'])
  self.assertEqual(self.f.buffers.items['target/a.c']['text'],'unsaved');self.assertEqual((self.project/'target/a.c').read_text(),'disk')
 def test_hilo_repeated_apply_uses_the_same_work(self):
  self.file('a.c');(self.project/'target').mkdir();plan=self.plan(['a.c'],'target');first=self.org.apply(self.ws,{'plan':plan['id']});second=self.org.apply(self.ws,{'plan':plan['id']});self.assertEqual(first,second)
  deadline=time.monotonic()+5
  while time.monotonic()<deadline and self.f.hilo.jobs[first['job']]['state'] in ('queued','running'):time.sleep(.02)
  self.assertEqual(self.f.hilo.jobs[first['job']]['state'],'done',self.f.hilo.jobs[first['job']]['error'])
 def test_lantern_active_file_cannot_be_moved_under_its_running_session(self):
  self.file('a.py');(self.project/'target').mkdir();plan=self.plan(['a.py'],'target')
  with patch.object(self.f.lantern,'snapshot',return_value={'active':True,'path':'a.py'}):
   with self.assertRaisesRegex(ValueError,'Lantern'):self.commit(plan)
  self.assertTrue((self.project/'a.py').exists())
 def test_python_health_uses_real_environment_without_running_project(self):
  identity='a'*32;directory=self.f.tern.directory(self.ws,identity);directory.mkdir(parents=True)
  (directory/'owner.json').write_text(json.dumps({'schema':1,'id':identity}))
  subprocess.run([sys.executable,'-m','venv','--without-pip',str(directory/'environment')],check=True,capture_output=True)
  self.f.tern.sessions[identity]={'id':identity,'kind':'python','workspace':str(self.ws.root)}
  self.file('main.py','raise RuntimeError("must never execute")')
  health=self.f.tern.check(self.ws,identity,threading.Event());self.assertTrue(health['ready']);self.assertTrue(health['isolated']);self.assertIn('environment',health['executable'])
 def test_vm_preflight_reports_missing_disk_without_booting(self):
  with patch.object(self.f.machines,'vm_base',return_value={'qemu':sys.executable}),patch.object(self.f.hacker,'_terminal',side_effect=AssertionError('must not boot')):
   health=self.f.machines.readiness({'disk':str(self.project/'missing.qcow2'),'memory':1024})
  self.assertFalse(health['ready']);self.assertIn('Disco de la sesión',[c['name'] for c in health['checks'] if not c['ok']])
 def test_real_vscode_extension_receives_rename_and_dirty_document(self):
  import io,zipfile
  self.file('a.py');(self.project/'target').mkdir();raw=io.BytesIO()
  plugin="""const v=require('vscode');exports.activate=()=>{const events=[];v.workspace.onDidRenameFiles(e=>events.push(e.files.map(f=>({old:f.oldUri.fsPath,next:f.newUri.fsPath,typed:f.newUri instanceof v.Uri}))));v.commands.registerCommand('qa.renames',()=>({events,current:v.window.activeTextEditor?.document.fileName,text:v.window.activeTextEditor?.document.getText(),dirty:v.window.activeTextEditor?.document.isDirty}));};"""
  with zipfile.ZipFile(raw,'w') as archive:
   archive.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'organizer','version':'1.0.0','main':'main.cjs'}));archive.writestr('extension/main.cjs',plugin)
  ticket=self.f.extensions.inspect_bytes(raw.getvalue())['ticket'];self.f.extensions.install(ticket,True);self.f.extension_runtime.start(self.ws,'qa.organizer',True)
  query=lambda **extra:self.f.extension_runtime.request(self.ws,{'id':'qa.organizer','method':'command','command':'qa.renames',**extra})['result']
  query(document={'path':'a.py','text':'unsaved','language':'python','dirty':True})
  self.commit(self.plan(['a.py'],'target'));deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   result=query()
   if result['events']:break
   time.sleep(.02)
  self.assertEqual(len(result['events']),1);self.assertTrue(result['events'][0][0]['typed']);self.assertTrue(result['current'].endswith('target\\a.py') or result['current'].endswith('target/a.py'));self.assertEqual(result['text'],'unsaved');self.assertTrue(result['dirty'])

if __name__=='__main__':unittest.main()
