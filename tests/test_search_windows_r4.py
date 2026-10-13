"""Search locations and terminal view ownership regression checks."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock,MagicMock,patch
from types import SimpleNamespace
from backend.native import NativeCore
from backend.workspace import Workspace
from backend.terminals import TerminalSession
from backend.desktop import DesktopAPI
from backend.buffers import Buffers
from backend.platform_services import PlatformServices

ROOT=Path(__file__).resolve().parents[1]

class SearchWindowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.ws=Workspace(self.root,NativeCore(ROOT))
    def tearDown(self):self.tmp.cleanup()
    def test_filters_before_limit(self):
        (self.root/'aaa.txt').write_text('needle\n'*220)
        (self.root/'src').mkdir();(self.root/'src/last.py').write_text('needle\n')
        hits=self.ws.search('needle',content=True,include='**/*.py',limit=201)
        self.assertEqual([(h['path'],h['line']) for h in hits],[('src/last.py',1)])
        self.assertEqual(len(self.ws.search('needle',content=True,exclude='aaa.txt')),1)
        self.assertEqual(len(self.ws.search('needle',content=True,file_type='code')),1)
    def test_case_word_and_literal(self):
        (self.root/'a.py').write_text('Alpha alphabet ALPHA\na.b aXb\n')
        self.assertEqual(len(self.ws.search('Alpha',content=True,case=True)[0]['matches']),1)
        self.assertEqual(len(self.ws.search('alpha',content=True,word=True)[0]['matches']),2)
        self.assertEqual(self.ws.search('a.b',content=True)[0]['text'],'a.b aXb')
        self.assertEqual(self.ws.search('ALpHa',content=True,case=True),[])
    def test_each_line_has_utf16_column_and_highlight(self):
        (self.root/'a.py').write_text('😀 needle\n  needle\n'+('x'*210)+' needle\n',encoding='utf-8')
        hits=self.ws.search('needle',content=True)
        self.assertEqual([(h['line'],h['column']) for h in hits],[(1,4),(2,3),(3,212)])
        self.assertEqual(hits[0]['matches'],[{'start':3,'end':9}])
        self.assertTrue(hits[-1]['text'].startswith('…'))
    def test_folder_scope_and_filter_limits(self):
        (self.root/'a.py').write_text('needle');(self.root/'src').mkdir();(self.root/'src/a.py').write_text('needle')
        self.assertEqual(len(self.ws.search('needle',content=True,folder='src')),1)
        with self.assertRaises(ValueError):self.ws.search('needle',include='x'*1025)
        with self.assertRaises((ValueError,PermissionError)):self.ws.search('needle',folder='../')
    def test_only_claimed_view_resizes_terminal(self):
        t=TerminalSession.__new__(TerminalSession);t.lock=threading.RLock();t.closed=False;t.resize_owner='';t.win=Mock()
        t.claim('editor-1');self.assertFalse(t.resize(100,20,'main-1'));t.win.setwinsize.assert_not_called()
        self.assertTrue(t.resize(100,20,'editor-1'));t.win.setwinsize.assert_called_once_with(20,100)
        t.claim('main-1');self.assertFalse(t.resize(45,9,'editor-1'));self.assertTrue(t.resize(120,25,'main-1'))
        with self.assertRaises(ValueError):t.claim('bad view!')
        t.closed=True;self.assertFalse(t.resize(100,20,'main-1'))
    def test_native_editor_can_detach_terminal_and_return_to_editor(self):
        api=DesktopAPI();api._panel='editor';api._owner=Mock();api._window=MagicMock();api._url='http://127.0.0.1:1';api._application=SimpleNamespace(workspace=self.ws)
        with patch('webview.create_window',return_value=MagicMock()) as create:
            self.assertTrue(api.detach_panel('console')['opened']);self.assertIn('parentPanel=editor',create.call_args.args[1]);api._window.destroy.assert_not_called()
            child_api=create.call_args.kwargs['js_api'];self.assertIs(child_api._owner,api)
    def test_only_open_session_external_file_can_be_detached(self):
        with tempfile.TemporaryDirectory() as tmp:
            external=Path(tmp)/'external.py';external.write_text('draft')
            api=DesktopAPI();api._window=MagicMock();api._url='http://127.0.0.1:1';buffers=Buffers();api._application=SimpleNamespace(workspace=self.ws,features=SimpleNamespace(buffers=buffers))
            self.ws.trusted=True
            with self.assertRaises(PermissionError):api.detach_panel('editor',str(external))
            buffers.update(self.ws,{'path':str(external),'text':'unsaved','saved':False})
            with patch('webview.create_window',return_value=MagicMock()) as create:
                self.assertTrue(api.detach_panel('editor',str(external))['opened']);self.assertIn('external.py',create.call_args.args[1])
    def test_execution_scope_requires_open_file_and_trust(self):
        f=PlatformServices.__new__(PlatformServices);f.app=SimpleNamespace(workspace=self.ws);f.buffers=Buffers();self.ws.trusted=True
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'outside.py';file.write_text('print(42)')
            with self.assertRaises(PermissionError):f.execution_workspace(self.ws,str(file))
            f.buffers.update(self.ws,{'path':str(file),'text':'print(42)','saved':True})
            scoped,name=f.execution_workspace(self.ws,str(file));self.assertEqual(scoped.root,file.parent);self.assertEqual(name,file.name);self.assertTrue(scoped.trusted)
            self.ws.trusted=False
            with self.assertRaises(PermissionError):f.execution_workspace(self.ws,str(file))

if __name__=='__main__':unittest.main()
