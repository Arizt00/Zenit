import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.accounts import interactive_argv, _supports_no_daemon
from backend.hilo import Hilo
from backend.tern import Tern
from tests import test_hilo_tern as fixtures
wait=fixtures.wait


class ClientLaunchTests(unittest.TestCase):
    def tearDown(self): _supports_no_daemon.cache_clear()

    def test_interactive_codex_uses_supported_direct_mode_and_keeps_argument_boundaries(self):
        with patch('backend.accounts.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='Options: --no-daemon')) as run:
            argv=['C:/a path/node.exe','C:/a path/codex.js']
            self.assertEqual(interactive_argv('codex', argv), argv+['--no-daemon'])
            self.assertEqual(interactive_argv('codex', argv), argv+['--no-daemon'])
            self.assertEqual(run.call_args.args[0], argv+['--help']);self.assertEqual(run.call_count,1)
            self.assertNotIn('shell',run.call_args.kwargs)

    def test_older_and_other_clients_keep_their_arguments(self):
        for result in (SimpleNamespace(returncode=0,stdout='Old help'),SimpleNamespace(returncode=1,stdout='--no-daemon')):
            _supports_no_daemon.cache_clear()
            with patch('backend.accounts.subprocess.run',return_value=result):self.assertEqual(interactive_argv('codex',['old.exe']),['old.exe'])
        with patch('backend.accounts.subprocess.run') as run:
            self.assertEqual(interactive_argv('claude-code',['claude.exe']),['claude.exe']);run.assert_not_called()


class HiloProgressTests(unittest.TestCase):
    def test_phase_and_priority_queue_position_follow_work(self):
        hilo=Hilo(None);started=threading.Event();release=threading.Event()
        def operation(event):hilo.report(event,'Creating disk');started.set();release.wait(3)
        try:
            first=hilo.submit('VM',operation);self.assertTrue(started.wait(2))
            slow=hilo.submit('Packages',lambda event:None,priority=10)
            fast=hilo.submit('Close',lambda event:None,priority=0)
            jobs={j['id']:j for j in hilo.snapshot()['jobs']}
            self.assertEqual(jobs[first['job']]['stage'],'Creating disk')
            self.assertEqual(jobs[fast['job']]['queuePosition'],1);self.assertEqual(jobs[slow['job']]['queuePosition'],2)
            self.assertGreaterEqual(jobs[first['job']]['elapsedMs'],0)
            release.set();self.assertEqual(wait(hilo,first['job'])['state'],'done')
        finally:release.set();hilo.shutdown()


class EnvironmentOptionsTests(unittest.TestCase):
    setUp=fixtures.TernTests.setUp
    tearDown=fixtures.TernTests.tearDown
    def test_clean_python_has_no_inherited_site_packages(self):
        task=self.features.post('/lantern/environments/create',{'kind':'python','name':'Clean','inherit':False})
        job=wait(self.features.hilo,task['job'],90);self.assertEqual(job['state'],'done',job)
        identity=job['result']['environment'];tern=self.features.tern;directory=tern.directory(self.app.workspace,identity)
        result=subprocess.run([str(tern.python(directory)),'-c','import site;print(site.ENABLE_USER_SITE)'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.stdout.strip(),'False')
        self.assertIn('include-system-site-packages = false',(directory/'environment/pyvenv.cfg').read_text())
        tern.save(self.app.workspace,identity,'clean.tern');tern.stop(self.app.workspace,identity);tern.reopen(self.app.workspace,'clean.tern')
        self.assertFalse(tern.get(self.app.workspace,identity)['inherit'])

    def test_vm_resources_are_validated_and_roundtrip_with_checkpoint(self):
        ws=self.app.workspace;tern=self.features.tern
        def create(**kwargs):
            directory=kwargs['directory'];(directory/'disk.qcow2').write_bytes(b'test');(directory/'seed.iso').write_bytes(b'test')
            return {'id':kwargs['identity'],'disk':str(directory/'disk.qcow2'),'seed':str(directory/'seed.iso')}
        with patch.object(self.features.machines,'create_arch',side_effect=create),patch.object(self.features.machines,'stop'):
            result=tern.create(ws,{'kind':'arch','memory':4096,'cpus':2},threading.Event());identity=result['environment']
            tern.save(ws,identity,'vm.tern');tern.stop(ws,identity);tern.reopen(ws,'vm.tern')
            self.assertEqual(tern.get(ws,identity)['profile']['memory'],4096);self.assertEqual(tern.get(ws,identity)['profile']['cpus'],2)
        for body in ({'memory':0},{'memory':True},{'cpus':99},{'cpus':'2'},[]):
            with self.assertRaises(ValueError):tern.resources(body)
