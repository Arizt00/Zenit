import base64
import json
import tempfile
import unittest
from pathlib import Path
from backend.workspace import Workspace
from backend.melody_lab import research
from backend.debug_manager import DebugManager
from backend.debug_adapters import ProtocolDebugger


class NativeStub:
    def stats(self,text):return {'lines':len(text.splitlines())}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.ws=Workspace(self.root,NativeStub())
        (self.root/'a.py').write_text('count = 1\n');self.body={'path':'a.py','content':'count = 2\n','diagnostics':[{'message':'Unknown name 12','line':1,'severity':'error'}]}
    def tearDown(self):self.tmp.cleanup()
    def tool(self,action,**changes):return research(self.ws,{**self.body,'action':action,**changes})
    def test_capsules_freeze_unsaved_evidence_and_bound_storage(self):
        for n in range(14):self.tool('capsule',content='count = '+str(n))
        data=json.loads((self.root/'.lumen/melody/capsules.json').read_text());self.assertEqual(len(data),12)
        self.assertEqual(data[-1]['content'],'count = 13');self.assertEqual((self.root/'a.py').read_text(),'count = 1\n')
    def test_drift_compares_hash_and_actual_source(self):
        with self.assertRaises(ValueError):self.tool('drift')
        self.tool('capsule');self.assertFalse(self.tool('drift')['changed'])
        result=self.tool('drift',content='count = 3\n');self.assertTrue(result['changed']);self.assertIn('+count = 3',result['diff'])
    def test_static_import_evidence_is_ast_based(self):
        (self.root/'b.py').write_text('import a\n# import a fake\ntext = "import a"\n')
        result=self.tool('impact');self.assertEqual(result['relations'],[{'path':'b.py','line':1,'reference':'a','kind':'Python import (static)'}])
    def test_fault_groups_and_handoff_use_observed_evidence(self):
        result=self.tool('faults',diagnostics=[{'message':'Error 12'},{'message':'Error 14'}],output='okay\nValueError: failed')
        self.assertEqual(len(result['groups']),1);self.assertEqual(len(result['groups'][0]['evidence']),2)
        self.assertEqual(result['outputSignals'],['ValueError: failed']);self.assertIn('Unknown name 12',self.tool('handoff')['brief'])
    def test_research_rejects_outside_paths_and_oversized_buffers(self):
        with self.assertRaises(PermissionError):self.tool('capsule',path='../outside')
        with self.assertRaises(ValueError):self.tool('capsule',content='a'*300001)
    def test_binary_bytes_pages_and_text_remain_distinct(self):
        raw=b'MZ\x00'+bytes(range(256))*8;(self.root/'program.exe').write_bytes(raw)
        item=self.ws.open_file('program.exe');self.assertEqual(item['format'],'PE executable');self.assertTrue(item['readOnly']);self.assertEqual(item['count'],512)
        page=self.ws.binary('program.exe',512);self.assertEqual(base64.b64decode(page['data']),raw[512:1024])
        self.assertEqual(self.ws.open_file('a.py')['content'],'count = 1\n')
        with self.assertRaises(ValueError):self.ws.read('program.exe')
        with self.assertRaises(ValueError):self.ws.binary('program.exe',len(raw)+1)
        with self.assertRaises(ValueError):self.ws.binary('program.exe',0,4097)
        with self.assertRaises(PermissionError):self.ws.binary('../outside')
    def test_binary_large_sparse_file_uses_bounded_read(self):
        with (self.root/'large.bin').open('wb') as f:f.seek(10_000_000);f.write(b'\x01')
        item=self.ws.open_file('large.bin');self.assertEqual(item['size'],10_000_001);self.assertEqual(len(base64.b64decode(item['data'])),512)
    def test_utf8_character_across_sampling_boundary_stays_text(self):
        text='a'*8191+'€\n';(self.root/'utf8.txt').write_text(text,encoding='utf-8');self.assertEqual(self.ws.open_file('utf8.txt')['content'],text)


class MachineTests(unittest.TestCase):
    def setUp(self):
        self.manager=DebugManager(None,None);self.adapter=ProtocolDebugger();self.manager.current=self.adapter
        self.adapter.update(status='paused',path='main.c',line=3,variables=[{'name':'n','value':'1'}],stack=[],machineCapabilities={'memory':True,'disassembly':True});self.calls=[]
        def request(method,args,**kwargs):
            self.calls.append((method,args));return {'address':'0x1000','data':base64.b64encode(b'\x01\x02').decode()} if method=='readMemory' else {'instructions':[{'address':'0x1000','instruction':'ret'}]}
        self.adapter.request=request
    def test_memory_and_disassembly_use_capability_checked_dap_requests(self):
        self.manager.machine({'operation':'memory','reference':'0x1000','count':2});self.manager.machine({'operation':'disassembly','reference':'0x1000','count':1})
        self.assertEqual(self.calls[0],('readMemory',{'memoryReference':'0x1000','count':2}));self.assertEqual(self.calls[1][0],'disassemble')
    def test_machine_requires_pause_and_enforces_bounds(self):
        with self.assertRaises(ValueError):self.manager.machine({'operation':'memory','reference':'0x1000','count':1})
        with self.assertRaises(ValueError):self.manager.machine({'operation':'disassembly','reference':'x','count':257})
        self.adapter.update(status='running')
        with self.assertRaises(ValueError):self.manager.machine({'operation':'memory','reference':'x'})
        self.assertEqual(len(self.calls),1)
    def test_observed_pause_history_is_deduplicated_bounded_and_detached(self):
        self.assertEqual(len(self.manager.snapshot()['pauseHistory']),1);self.assertEqual(len(self.manager.snapshot()['pauseHistory']),1)
        for n in range(30):self.adapter.update(line=n+4,variables=[{'name':'n','value':str(n)}]);self.manager.snapshot()
        state=self.manager.snapshot();self.assertEqual(len(state['pauseHistory']),24);state['pauseHistory'][0]['variables'].clear();self.assertTrue(self.manager.snapshot()['pauseHistory'][0]['variables'])
    def test_resumed_process_discards_inflight_machine_result(self):
        def request(*args,**kwargs):self.adapter.update(status='running');return {'data':''}
        self.adapter.request=request
        with self.assertRaises(ValueError):self.manager.machine({'operation':'memory','reference':'x'})

if __name__=='__main__':unittest.main()
