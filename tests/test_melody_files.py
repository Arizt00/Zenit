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
