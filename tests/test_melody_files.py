"""Disk transaction tests; deterministic proposals do not certify model quality."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.buffers import Buffers
from backend.melody_files import MelodyFiles
from backend.workspace import Workspace, ConflictError


class MelodyFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ws=Workspace(self.root,None);self.ws.trusted=True
        self.jobs={};self.events=[]
        platform=SimpleNamespace(buffers=Buffers(),ai=SimpleNamespace(get=lambda key:self.jobs[key]),extension_services=SimpleNamespace(emit=lambda *a,**kw:self.events.append((a,kw))),prefs=SimpleNamespace(audit=lambda *a,**kw:None))
        self.files=MelodyFiles(platform)
    def plan(self,ops,delete=False):
        self.jobs['job']=SimpleNamespace(file_workspace=str(self.root),file_delete_allowed=delete,done=True,error='',cancelled=threading.Event(),text=json.dumps({'summary':'Revisión','operations':ops}))
        return self.files.review(self.ws,'job')
    def requested_plan(self,question,ops,path=''):
        request=self.files.prepare(self.ws,{'question':question,'path':path})
        self.jobs['job']=SimpleNamespace(file_workspace=str(self.root),file_delete_allowed=self.files.deletion_requested(question),file_snapshots=request['fileSnapshots'],file_session=request['fileSession'],done=True,error='',cancelled=threading.Event(),text=json.dumps({'summary':'Petición explícita','operations':ops}))
        return self.files.review(self.ws,'job'),request
    def test_project_create_update_delete_and_recover(self):
        (self.root/'old.py').write_bytes(b'# old\r\n');(self.root/'keep.py').write_text('old')
        plan=self.plan([{'kind':'create','path':'project/src/main.py','content':'print(42)\n'},{'kind':'update','path':'keep.py','content':'new'},{'kind':'delete','path':'old.py'}],True)
        self.assertFalse((self.root/'project').exists());receipt=self.files.commit(self.ws,plan['ticket'],True)
        self.assertEqual((self.root/'project/src/main.py').read_text(),'print(42)\n');self.assertFalse((self.root/'old.py').exists());self.assertEqual((self.root/'keep.py').read_text(),'new')
        self.files.undo(self.ws,receipt['receipt']);self.assertEqual((self.root/'old.py').read_bytes(),b'# old\r\n');self.assertEqual((self.root/'keep.py').read_text(),'old');self.assertFalse((self.root/'project').exists());self.assertEqual(len(self.events),2)
    def test_no_delete_without_explicit_scope(self):
        (self.root/'old.py').write_text('data')
        with self.assertRaises(PermissionError):self.plan([{'kind':'delete','path':'old.py'}])
        self.assertTrue((self.root/'old.py').exists())
    def test_boundary_private_paths_and_collisions(self):
        for path in ('../outside.py','/outside.py','C:/outside.py','.git/config','.lumen/profile','.env','folder/credentials.json','node_modules/a.js','CON','a\\b.py'):
            with self.subTest(path=path),self.assertRaises((ValueError,PermissionError)):self.plan([{'kind':'create','path':path,'content':'x'}])
        with self.assertRaises(ValueError):self.plan([{'kind':'create','path':'a','content':'x'},{'kind':'create','path':'a/b','content':'x'}])
        with self.assertRaises(ValueError):self.plan([{'kind':'create','path':'a','content':'x'},{'kind':'create','path':'a','content':'y'}])
    def test_stale_disk_plan_changes_nothing(self):
        (self.root/'old.py').write_text('original');plan=self.plan([{'kind':'create','path':'new.py','content':'new'},{'kind':'update','path':'old.py','content':'proposal'}]);(self.root/'old.py').write_text('external')
        with self.assertRaises(ConflictError):self.files.commit(self.ws,plan['ticket'],True)
        self.assertFalse((self.root/'new.py').exists());self.assertEqual((self.root/'old.py').read_text(),'external')
    def test_unsaved_detached_buffer_blocks_apply_and_undo(self):
        (self.root/'old.py').write_text('original');plan=self.plan([{'kind':'update','path':'old.py','content':'proposal'}]);buffers=self.files.platform.buffers
        buffers.update(self.ws,{'path':'old.py','text':'unsaved'})
        with self.assertRaises(ConflictError):self.files.commit(self.ws,plan['ticket'],True)
        buffers.clear();receipt=self.files.commit(self.ws,plan['ticket'],True);buffers.update(self.ws,{'path':'old.py','text':'later'})
        with self.assertRaises(ConflictError):self.files.undo(self.ws,receipt['receipt'])
        self.assertEqual((self.root/'old.py').read_text(),'proposal')
    def test_write_failure_rolls_back_existing_and_created_files(self):
        (self.root/'old.py').write_text('original');plan=self.plan([{'kind':'update','path':'old.py','content':'changed'},{'kind':'create','path':'nested/new.py','content':'new'}]);replace=self.files.replace;calls=[]
        def failing(path,raw):
            calls.append(path)
            if len(calls)==2:raise OSError('disk failure')
            return replace(path,raw)
        with patch.object(self.files,'replace',side_effect=failing),self.assertRaises(OSError):self.files.commit(self.ws,plan['ticket'],True)
        self.assertEqual((self.root/'old.py').read_text(),'original');self.assertFalse((self.root/'nested').exists());self.assertEqual(self.events,[])
    def test_undo_wont_overwrite_later_edit(self):
        plan=self.plan([{'kind':'create','path':'new.py','content':'new'}]);receipt=self.files.commit(self.ws,plan['ticket'],True);(self.root/'new.py').write_text('later')
        with self.assertRaises(ConflictError):self.files.undo(self.ws,receipt['receipt'])
        self.assertEqual((self.root/'new.py').read_text(),'later')
    def test_consultation_cancelled_job_workspace_and_consent(self):
        plan=self.plan([{'kind':'create','path':'new.py','content':'new'}])
        with self.assertRaises(PermissionError):self.files.commit(self.ws,plan['ticket'],False)
        self.jobs['job'].cancelled.set()
        with self.assertRaises(ValueError):self.files.review(self.ws,'job')
        self.jobs['job'].cancelled.clear();self.jobs['job'].file_workspace='elsewhere'
        with self.assertRaises(PermissionError):self.files.review(self.ws,'job')
        self.files.plans[plan['ticket']]['created']-=601
        with self.assertRaises(ConflictError):self.files.commit(self.ws,plan['ticket'],True)
    def test_requested_dirty_buffer_is_context_and_undo_restores_it(self):
        (self.root/'main.py').write_bytes(b'\xef\xbb\xbfprint(1)\r\n')
        buffers=self.files.platform.buffers;buffers.update(self.ws,{'path':'main.py','text':'print(2)\n','saved':False})
        plan,request=self.requested_plan('Modifica main.py para imprimir 3',[{'kind':'update','path':'main.py','content':'print(3)\n'}])
        self.assertEqual(request['fileContext'][0]['content'],'print(2)\n');self.assertEqual(plan['operations'][0]['before'],'print(2)\n')
        result=self.files.commit(self.ws,plan['ticket'],True)
        self.assertEqual((self.root/'main.py').read_bytes(),b'\xef\xbb\xbfprint(3)\r\n');self.assertTrue(buffers.items['main.py']['saved'])
        self.files.undo(self.ws,result['receipt']);self.assertEqual((self.root/'main.py').read_bytes(),b'\xef\xbb\xbfprint(1)\r\n')
        self.assertEqual(buffers.items['main.py']['text'],'print(2)\n');self.assertFalse(buffers.items['main.py']['saved'])
    def test_request_revision_cannot_be_replaced_during_generation(self):
        path=self.root/'main.py';path.write_text('original');request=self.files.prepare(self.ws,{'question':'Modifica main.py'})
        path.write_text('new edit')
        self.jobs['job']=SimpleNamespace(file_workspace=str(self.root),file_delete_allowed=False,file_snapshots=request['fileSnapshots'],file_session=request['fileSession'],done=True,error='',cancelled=threading.Event(),text=json.dumps({'operations':[{'kind':'update','path':'main.py','content':'model'}]}))
        with self.assertRaises(ConflictError):self.files.review(self.ws,'job')
        self.assertEqual(path.read_text(),'new edit')
    def test_named_binary_and_private_deletion_is_recoverable_without_remote_contents(self):
        raw=b'\x00\xffBINARY';(self.root/'asset.bin').write_bytes(raw);(self.root/'.env').write_text('KEY=private-fixture')
        plan,request=self.requested_plan('Borra asset.bin y elimina .env',[{'kind':'delete','path':'asset.bin'},{'kind':'delete','path':'.env'}])
        self.assertTrue(all(x['content'] is None for x in request['fileContext']))
        self.assertNotIn('private-fixture',json.dumps(request['fileContext']))
        result=self.files.commit(self.ws,plan['ticket'],True);self.assertFalse((self.root/'asset.bin').exists());self.files.undo(self.ws,result['receipt'])
        self.assertEqual((self.root/'asset.bin').read_bytes(),raw);self.assertEqual((self.root/'.env').read_text(),'KEY=private-fixture')
    def test_only_open_external_session_files_are_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'external.py';path.write_text('outside');self.files.platform.buffers.update(self.ws,{'path':str(path),'text':'outside','saved':True})
            plan,_=self.requested_plan('Modifica external.py',[{'kind':'update','path':path.as_posix(),'content':'changed'}])
            result=self.files.commit(self.ws,plan['ticket'],True);self.assertEqual(path.read_text(),'changed');self.files.undo(self.ws,result['receipt']);self.assertEqual(path.read_text(),'outside')
            other=Path(tmp)/'other.py';other.write_text('untouched')
            with self.assertRaises(PermissionError):self.requested_plan('Modifica external.py',[{'kind':'update','path':other.as_posix(),'content':'bad'}])
    def test_ambiguous_basename_and_unrequested_existing_file_are_rejected(self):
        for folder in ('a','b'):(self.root/folder).mkdir();(self.root/folder/'main.py').write_text(folder)
        with self.assertRaises(ValueError):self.files.prepare(self.ws,{'question':'Modifica main.py'})
        with self.assertRaises(PermissionError):self.requested_plan('Modifica a/main.py',[{'kind':'update','path':'b/main.py','content':'bad'}])
        with self.assertRaises(PermissionError):self.files.prepare(self.ws,{'question':'Explica cómo borrar a/main.py'})
        self.assertFalse(self.files.deletion_requested('Modifica a/main.py y no borres b/main.py'))
    def test_named_new_config_and_open_unsaved_draft_can_be_created(self):
        self.files.platform.buffers.update(self.ws,{'path':'new.py','text':'# unsaved draft','saved':False})
        plan,_=self.requested_plan('Crea new.py y .env.example',[{'kind':'create','path':'new.py','content':'print(42)'},{'kind':'create','path':'.env.example','content':'API_KEY='}])
        receipt=self.files.commit(self.ws,plan['ticket'],True);self.assertEqual((self.root/'new.py').read_text(),'print(42)')
        self.files.undo(self.ws,receipt['receipt']);self.assertFalse((self.root/'new.py').exists());self.assertEqual(self.files.platform.buffers.items['new.py']['text'],'# unsaved draft')
