import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.hilo import Hilo
from backend.server import Application
from backend.foundation import python_command
from backend.runner import Runner

ROOT = Path(__file__).resolve().parents[1]


def wait(hilo, identity, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = next(j for j in hilo.snapshot()['jobs'] if j['id'] == identity)
        if job['state'] not in ('queued', 'running'): return job
        time.sleep(.03)
    raise AssertionError('Hilo did not complete within the test deadline.')


class HiloTests(unittest.TestCase):
    def test_clear_finished_keeps_running_jobs_and_other_workspaces(self):
        hilo=Hilo(None);started=threading.Event();release=threading.Event()
        try:
            first=hilo.submit('Finished',lambda event:None,workspace='one');wait(hilo,first['job'])
            other=hilo.submit('Other workspace',lambda event:None,workspace='two');wait(hilo,other['job'])
            active=hilo.submit('Running',lambda event:(started.set(),release.wait(3)),workspace='one');self.assertTrue(started.wait(2))
            self.assertEqual(hilo.snapshot('one')['counts']['running'],1)
            self.assertEqual(hilo.clear_finished('one'),{'removed':1})
            self.assertEqual({j['id'] for j in hilo.snapshot()['jobs']},{other['job'],active['job']})
        finally:release.set();hilo.shutdown()

    def test_queue_priority_dedup_cancellation_and_cache(self):
        hilo = Hilo(None); started = threading.Event(); release = threading.Event(); order = []
        try:
            first = hilo.submit('First', lambda event: (started.set(), release.wait(3)), key='same')
            self.assertTrue(started.wait(2))
            self.assertEqual(first, hilo.submit('Duplicate', lambda event: self.fail('duplicate ran'), key='same'))
            slow = hilo.submit('Maintenance', lambda event: order.append('maintenance'), priority=10)
            fast = hilo.submit('Console', lambda event: order.append('console'), priority=0)
            cancelled = hilo.submit('Cancelled', lambda event: self.fail('cancelled task ran'))
            hilo.cancel(cancelled['job']); release.set()
            wait(hilo, slow['job']); self.assertEqual(wait(hilo, fast['job'])['state'], 'done')
            self.assertEqual(wait(hilo, cancelled['job'])['state'], 'cancelled'); self.assertEqual(order, ['console', 'maintenance'])
            value = hilo.cached('inventory', lambda: {'items': [1]}); value['items'].append(2)
            self.assertEqual(hilo.cached('inventory', lambda: self.fail('cache missed')), {'items': [1]})
            hilo.invalidate(); self.assertEqual(hilo.cached('inventory', lambda: [3]), [3])
        finally: release.set(); hilo.shutdown()

    def test_real_package_process_queue_leaves_foreground_free(self):
        hilo = Hilo(None); runner = Runner(); gate = threading.Event(); started = threading.Event()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                hilo.submit('Block maintenance', lambda event: (started.set(), gate.wait(3))); started.wait(2)
                background = runner.start([[sys.executable, '-c', 'print("package finished")']], Path(tmp), scheduler=hilo)
                job = runner.jobs[background['job']]; self.assertTrue(job.queued)
                foreground = runner.start([[sys.executable, '-c', 'print("foreground")']], Path(tmp))
                deadline = time.monotonic() + 5
                while not runner.jobs[foreground['job']].done and time.monotonic() < deadline: time.sleep(.03)
                self.assertEqual(runner.jobs[foreground['job']].code, 0); self.assertFalse(job.done)
                gate.set()
                pending = next(j for j in hilo.snapshot()['jobs'] if j['label'].startswith('Packages'))
                wait(hilo, pending['id']); self.assertEqual(job.code, 0); self.assertIn('package finished', job.output)
            finally: gate.set(); hilo.shutdown(); runner.shutdown()

    def test_package_failure_and_bounded_queue(self):
        hilo = Hilo(None); runner = Runner(); gate = threading.Event(); started = threading.Event()
        try:
            hilo.submit('Gate', lambda event: (started.set(), gate.wait(5))); self.assertTrue(started.wait(2))
            for i in range(24): hilo.submit(str(i), lambda event: None)
            with self.assertRaises(ValueError): hilo.submit('Overflow', lambda event: None)
            gate.set(); hilo.queue.join()
            with tempfile.TemporaryDirectory() as tmp:
                task = runner.start([[sys.executable, '-c', 'raise SystemExit(7)']], Path(tmp), scheduler=hilo)
                job = next(j for j in hilo.snapshot()['jobs'] if j['label'].startswith('Packages'))
                self.assertEqual(wait(hilo, job['id'])['state'], 'failed')
                self.assertEqual(runner.jobs[task['job']].code, 7)
        finally: gate.set(); hilo.shutdown(); runner.shutdown()


class TernTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zenit-tern-test-'); self.base = Path(self.temp.name)
        self.ws = self.base / 'project'; self.ws.mkdir(); (self.ws / 'main.py').write_text('print(42)\n')
        self.app = Application(ROOT, self.ws, data_dir=self.base / 'profile'); self.app.workspace.trusted = True
        self.features = self.app.features

    def tearDown(self):
        self.features.shutdown(); self.app.runner.shutdown(); self.temp.cleanup()

    def create(self, kind='python'):
        task = self.features.post('/lantern/environments/create', {'kind': kind, 'name': 'Test session'})
        job = wait(self.features.hilo, task['job'], 90)
        self.assertEqual(job['state'], 'done', job)
        return job['result']['environment']

    def test_real_python_interpreter_saved_checkpoint_and_temp_cleanup(self):
        ws = self.app.workspace; tern = self.features.tern; identity = self.create()
        directory = tern.directory(ws, identity); tern.activate(ws, identity)
        command = python_command(ws)
        self.assertEqual(Path(command[0]), tern.python(directory))
        result = subprocess.run(command + ['-c', 'import sys; print(sys.prefix)'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0); self.assertIn(str(directory), result.stdout)
        self.assertEqual(Path(self.features.python_packages.status(ws)['environment']['directory']), directory / 'environment')
        (directory / 'note.txt').write_text('keep this checkpoint')
        tern.save(ws, identity, 'experiment.tern')
        with self.assertRaises(Exception): tern.save(ws, identity, '../outside.tern')
        tern.stop(ws, identity); self.assertTrue(directory.exists()); self.assertEqual(ws.environment_path, '.venv')
        tern.reopen(ws, 'experiment.tern'); self.assertEqual((directory / 'note.txt').read_text(), 'keep this checkpoint')
        tern.stop(ws, identity)
        ephemeral = self.create(); scratch = tern.directory(ws, ephemeral)
        tern.stop(ws, ephemeral); self.assertFalse(scratch.exists()); self.assertEqual((self.ws / 'main.py').read_text(), 'print(42)\n')
        self.assertTrue((directory / 'note.txt').exists())

    def test_descriptor_guards_and_untrusted_execution(self):
        ws = self.app.workspace; tern = self.features.tern
        with self.assertRaises(ValueError): tern.directory(ws, '../outside')
        (self.ws / 'hostile.tern').write_text(json.dumps({'schema': 1, 'type': 'zenit-environment', 'id': '../outside', 'kind': 'arch'}))
        with self.assertRaises(ValueError): tern.reopen(ws, 'hostile.tern')
        ws.trusted = False
        with self.assertRaises(PermissionError): self.features.post('/lantern/environments/create', {'kind': 'python'})
        with self.assertRaises(PermissionError): self.features.connections.launch(ws, {'id': 'github'})

    def test_interpreter_restart_retires_lsp_and_preserves_restart_profile(self):
        ws = self.app.workspace; tern = self.features.tern; identity = self.create()
        profile = {'id': 'fixture', 'label': 'Fixture', 'argv': [sys.executable, str(ROOT / 'tests/fixtures/lsp_server.py')], 'languages': ['python']}
        self.features.tools.config['servers'].append(profile)
        server = self.features.lsp.start(ws, 'fixture', True)
        with patch.object(self.features.extension_services, 'emit') as emit:
            tern.activate(ws, identity)
            self.assertEqual(emit.call_args.kwargs['profiles'], ['fixture'])
        self.assertTrue(self.features.lsp.poll(server['id'], 0)['retired'])
        self.assertTrue(self.features.lsp.notify(server['id'], 'textDocument/didSave', {})['retired'])
        restarted = self.features.lsp.start(ws, 'fixture', True)
        self.assertNotEqual(restarted['id'], server['id'])
        self.features.lsp.stop(restarted['id'])

    def test_vm_base_configuration_rejects_incomplete_and_external_paths(self):
        machines = self.features.machines
        base = self.base / 'sdk'; base.mkdir()
        (base/'tool-index.json').write_text(json.dumps({'schema': 1, 'tools': {}, 'components': [{'id': 'arch', 'file': '../project/main.py'}]}))
        with self.assertRaises(ValueError): machines.configure_base(str(base))
        if machines.snapshot()['templates'][0]['available']:
            result = machines.configure_base(str(ROOT/'sdk/foundation'))
            self.assertTrue(result['templates'][0]['available'])
            self.assertEqual(json.loads(machines.base_index.read_text())['directory'], str(ROOT/'sdk/foundation'))

    def test_real_qcow_overlay_is_session_owned_and_saveable(self):
        if not self.features.tern.snapshot(self.app.workspace)['vm']: self.skipTest('QEMU and Arch image unavailable')
        ws = self.app.workspace; tern = self.features.tern; identity = self.create('arch')
        directory = tern.directory(ws, identity)
        self.assertEqual((directory / 'disk.qcow2').read_bytes()[:4], b'QFI\xfb')
        self.assertTrue((directory / 'seed.iso').is_file())
        self.assertFalse(any(p['id'] == identity for p in self.features.machines.profiles))
        tern.save(ws, identity, 'machine.tern'); tern.stop(ws, identity); tern.reopen(ws, 'machine.tern')
        self.assertEqual(tern.sessions[identity]['profile']['disk'], str(directory / 'disk.qcow2'))

    @unittest.skipUnless(os.environ.get('ZENIT_VM_LIVE_TEST') == '1', 'Opt-in live QEMU boot')
    def test_live_vm_boot_console_saved_disk_and_shutdown(self):
        ws = self.app.workspace; tern = self.features.tern; identity = self.create('arch')
        result = tern.console(ws, identity)
        terminal = self.features.terminals.sessions[result['terminal']['id']]
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            if 'zenit@zenit-arch' in terminal.output: break
            if terminal.closed: self.fail(terminal.output[-3000:])
            time.sleep(.5)
        else: self.fail('VM did not reach its console: ' + terminal.output[-3000:])
        terminal.write("printf 'TERN_%s\\n' LIVE > ~/checkpoint; cat ~/checkpoint\r")
        deadline = time.monotonic() + 15
        while 'TERN_LIVE' not in terminal.output and time.monotonic() < deadline: time.sleep(.1)
        self.assertIn('TERN_LIVE', terminal.output)
        tern.save(ws, identity, 'live.tern'); tern.stop(ws, identity)
        self.assertTrue(terminal.closed)
        tern.reopen(ws, 'live.tern'); self.assertTrue(tern.directory(ws, identity).joinpath('disk.qcow2').exists())
        print('PASS first VM boot, guest write and saved descriptor; checking the restored disk', flush=True)
        restored = tern.console(ws, identity)
        terminal = self.features.terminals.sessions[restored['terminal']['id']]
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            if 'zenit@zenit-arch' in terminal.output: break
            if terminal.closed: self.fail(terminal.output[-3000:])
            time.sleep(.5)
        else: self.fail('Restored VM did not reach its console: ' + terminal.output[-3000:])
        terminal.write('cat ~/checkpoint\r')
        deadline = time.monotonic() + 15
        while 'TERN_LIVE' not in terminal.output and time.monotonic() < deadline: time.sleep(.1)
        self.assertIn('TERN_LIVE', terminal.output)
        tern.stop(ws, identity)

    def test_external_adapter_argv_and_no_shell(self):
        ws = self.app.workspace; c = self.features.connections
        (self.ws / 'scene.blend').write_bytes(b'BLENDER')
        with patch.object(c, 'executable', return_value=['C:/Apps/Blender/blender.exe']), patch('backend.hilo.subprocess.Popen') as launch:
            launch.return_value.pid = 42
            result = c.launch(ws, {'id': 'blender', 'path': 'scene.blend'})
            self.assertEqual(result['pid'], 42); self.assertEqual(launch.call_args.args[0][-1], str(self.ws / 'scene.blend'))
            self.assertNotIn('shell', launch.call_args.kwargs)
            with self.assertRaises(PermissionError): c.launch(ws, {'id': 'blender', 'path': '../outside.blend'})
            with self.assertRaises(ValueError): c.launch(ws, {'id': 'unity'})


if __name__ == '__main__': unittest.main()
