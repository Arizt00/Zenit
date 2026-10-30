"""Recovery, evidence freshness and cancellation over disposable projects."""
import base64
import concurrent.futures
import copy
import tempfile
import threading
import time
import unittest
from concurrent.futures import CancelledError
from pathlib import Path

from backend.binary_recovery import normalize
from backend.hilo import Hilo
from backend.melody_dossier import dossier
from backend.server import Application
from backend.workbenches import Workbenches

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class SharedDiscoveryTests(unittest.TestCase):
    def wait_shared(self, hilo):
        end = time.monotonic() + 2
        while time.monotonic() < end:
            if hilo.cache_stats()['shared']:return
            time.sleep(.005)
        self.fail('The second reader did not share the discovery.')

    def test_invalidated_owner_and_waiter_both_receive_fresh_value(self):
        hilo = Hilo(None); entered = threading.Event(); release = threading.Event(); calls = []
        def read():
            calls.append(1); value = len(calls)
            if value == 1:entered.set(); release.wait(3)
            return {'value': value}
        try:
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                first = pool.submit(hilo.cached, 'tools', read)
                self.assertTrue(entered.wait(2))
                second = pool.submit(hilo.cached, 'tools', read); self.wait_shared(hilo)
                hilo.invalidate(); release.set()
                self.assertEqual(first.result(3), {'value': 2})
                self.assertEqual(second.result(3), {'value': 2})
            self.assertEqual(len(calls), 2)
            self.assertEqual(hilo.cache_stats()['discarded'], 1)
        finally:release.set(); hilo.shutdown()

    def test_cancelled_waiter_leaves_shared_discovery_available(self):
        hilo = Hilo(None); entered = threading.Event(); release = threading.Event(); cancel = threading.Event()
        try:
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                owner = pool.submit(hilo.cached, 'tools', lambda: (entered.set(), release.wait(3), 42)[-1])
                self.assertTrue(entered.wait(2))
                waiter = pool.submit(hilo.cached, 'tools', lambda: self.fail('duplicated'), cancel=cancel)
                self.wait_shared(hilo); cancel.set()
                with self.assertRaises(CancelledError):waiter.result(.5)
                self.assertFalse(owner.done()); release.set(); self.assertEqual(owner.result(2), 42)
            self.assertEqual(hilo.cached('tools', lambda: self.fail('lost shared result')), 42)
            with self.assertRaises(CancelledError):hilo.cached('tools', lambda: 1, cancel=cancel)
        finally:release.set(); hilo.shutdown()


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zenit-reliability-')
        self.base = Path(self.tmp.name); root = self.base/'project'; root.mkdir()
        (root/'main.py').write_text('from helper import VALUE\nprint(VALUE)\n', encoding='utf-8')
        (root/'helper.py').write_text('VALUE=7\n', encoding='utf-8')
        (root/'bytes.bin').write_bytes(bytes(range(256))*32)
        self.app = Application(ROOT, root, data_dir=self.base/'profile')
        self.ws = self.app.workspace; self.ws.trusted = True; self.f = self.app.features

    def tearDown(self):
        self.f.shutdown(); self.app.runner.shutdown(); self.tmp.cleanup()

    def binary_document(self):
        revision = self.ws.binary('bytes.bin')['revision']
        return {'path': 'bytes.bin', 'kind': 'binary', 'dirty': True, 'revision': revision,
                'binary': {'revision': revision, 'offset': 4096,
                           'patches': [{'offset': 4101, 'before': encoded(b'\x05\x06'), 'after': encoded(b'\xaa\xbb')}]}}

    def test_pending_bytes_survive_recreation_without_writing_the_source(self):
        before = self.ws.resolve('bytes.bin').read_bytes(); doc = self.binary_document()
        text = {'path':'main.py','dirty':True,'content':'unsaved text','revision':self.ws.read('main.py')['revision']}
        self.f.workbenches.checkpoint(self.ws, {'session': {'documents': [doc, text], 'active':'bytes.bin'}})
        recovered = Workbenches(self.f).snapshot(self.ws)['session']
        self.assertEqual(recovered['documents'][0]['binary'], doc['binary'])
        self.assertEqual(recovered['documents'][1]['content'], 'unsaved text')
        self.assertEqual(self.ws.resolve('bytes.bin').read_bytes(), before)
        # Changed on disk: recovery still retains the original revision and bytes.
        self.ws.resolve('bytes.bin').write_bytes(b'changed on disk')
        self.assertEqual(Workbenches(self.f).snapshot(self.ws)['session']['documents'][0]['binary'], doc['binary'])

    def test_named_space_never_embeds_pending_bytes_or_overwrites_recovery(self):
        doc = self.binary_document(); store = self.f.workbenches
        store.checkpoint(self.ws, {'session': {'documents':[doc]}})
        store.save_space(self.ws, {'name':'Inspect','session': {'documents':[doc]}})
        state = store.snapshot(self.ws)
        self.assertNotIn('binary', state['spaces'][0]['session']['documents'][0])
        self.assertFalse(state['spaces'][0]['session']['documents'][0]['dirty'])
        self.assertEqual(state['session']['documents'][0]['binary'], doc['binary'])

    def test_invalid_patch_payloads_are_rejected(self):
        valid = self.binary_document()['binary']
        variants = [dict(valid,revision=None),dict(valid,offset=-1)]
        for group in ({'offset':-1,'before':'AA==','after':'AQ=='},
                      {'offset':0,'before':'!!!','after':'AA=='},
                      {'offset':0,'before':'AA==','after':'AQI='}):
            variants.append(dict(valid,patches=[group]))
        variants.append(dict(valid,patches=[valid['patches'][0]]*2))
        group = {'offset':0,'before':encoded(bytes(4096)),'after':encoded(bytes([1])*4096)}
        variants.append(dict(valid,patches=[dict(group,offset=i*4096) for i in range(17)]))
        for value in variants:
            with self.subTest(value=str(value)[:150]),self.assertRaises(ValueError):normalize(value)

    def complete(self, version):
        end = time.monotonic()+20
        while time.monotonic()<end:
            state = self.f.lantern.snapshot()
            if state.get('bufferVersion')==version and state.get('executedGeneration')==state.get('generation') and state.get('code') is not None:return state
            time.sleep(.03)
        self.fail(str(state))

    def test_evidence_tracks_dependencies_commands_environment_and_history(self):
        content = self.ws.read('main.py')['content']
        self.f.lantern.start(self.ws,'main.py',content,1); self.complete(1)
        first = dossier(self.f,self.ws,{'path':'main.py','content':content})['execution']
        self.assertTrue(first['currentEvidence']); self.assertTrue(first['commands'])
        self.assertEqual(first['target']['id'],'local')
        self.ws.resolve('helper.py').write_text('VALUE=8\n',encoding='utf-8')
        stale = dossier(self.f,self.ws,{'path':'main.py','content':content})['execution']
        self.assertTrue(stale['matchesBuffer']); self.assertFalse(stale['currentEvidence'])
        self.assertIn('helper.py', stale['contextVerification']['changed'])
        self.f.lantern.buffer(self.ws,'main.py',content,2); self.complete(2)
        self.assertTrue(dossier(self.f,self.ws,{'path':'main.py'})['execution']['currentEvidence'])
        self.f.runtimes.config['languages']['qa-evidence']={'extensions':['.qa-evidence']}
        configured=dossier(self.f,self.ws,{'path':'main.py'})['execution']
        self.assertFalse(configured['matchesConfiguration']);self.assertFalse(configured['currentEvidence'])
        del self.f.runtimes.config['languages']['qa-evidence']
        self.ws.environment_path = '.different-environment'
        report = dossier(self.f,self.ws,{'path':'main.py'})['execution']
        self.assertFalse(report['matchesEnvironment']); self.assertFalse(report['currentEvidence'])
        self.f.lantern.stop()
        self.assertTrue(self.f.lantern.history[-1]['context']['files'])
        self.assertTrue(self.f.lantern.history[-1]['commands'])

    def test_build_descriptors_invalidate_evidence_but_secrets_are_not_scanned(self):
        self.ws.resolve('Cargo.toml',must_exist=False).write_text('[package]\nname="example"\n')
        self.ws.resolve('.env',must_exist=False).write_text('PRIVATE_SECRET=never-send-this')
        content = self.ws.read('main.py')['content']; self.f.lantern.start(self.ws,'main.py',content,1); self.complete(1)
        self.ws.resolve('Cargo.toml').write_text('[package]\nname="changed"\n')
        report = dossier(self.f,self.ws,{'path':'main.py'})
        self.assertIn('Cargo.toml', report['execution']['contextVerification']['changed'])
        self.assertNotIn('PRIVATE_SECRET',str(report))

    def test_performance_report_never_starts_discovery_or_programs(self):
        before = copy.deepcopy(self.f.hilo.cache_stats()); jobs = len(self.app.runner.jobs)
        report = self.f.get('/performance',{})
        self.assertGreaterEqual(report['backendInitializationMs'],0)
        self.assertEqual(self.f.hilo.cache_stats(), before)
        self.assertEqual(len(self.app.runner.jobs),jobs)

    def test_evidence_limits_do_not_reduce_lantern_buffer_capacity(self):
        source='# long source\n'*11000+'print(7)\n'
        self.assertGreater(len(source.encode()),128000)
        self.f.lantern.start(self.ws,'main.py',source,1)
        state=self.complete(1);self.assertEqual(state['code'],0)
        self.assertTrue(self.f.lantern.job.lantern_context['limited'])


if __name__=='__main__':unittest.main()
