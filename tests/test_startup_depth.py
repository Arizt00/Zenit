import concurrent.futures,json,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from backend.server import Application
from backend.startup_metrics import StartupMetrics
from backend.deferred_services import FACTORIES
from backend.orchestration import Kernel
from backend.machine_acceleration import cpu_arguments,probe
from backend.language_verification import signature,reference

ROOT=Path(__file__).resolve().parents[1]

class StartupDepthTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='zenit-startup-depth-');self.root=Path(self.tmp.name);(self.root/'project').mkdir()
  self.app=Application(ROOT,self.root/'project',data_dir=self.root/'profile');self.f=self.app.features
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def test_reports_workspace_change_and_shutdown_never_construct_unused_services(self):
  self.assertFalse(set(FACTORIES)&set(self.f.__dict__))
  self.f.state();report=self.f.get('/performance',{});self.assertTrue(report['backendTimings']['phases']);self.assertEqual(report['machines'],[])
  self.f.workspace_changed();self.f.shutdown()
  self.assertFalse(set(FACTORIES)&set(self.f.__dict__))
  with self.assertRaisesRegex(RuntimeError,'cerrando'):self.f.machines
 def test_concurrent_first_use_constructs_exactly_once_and_kernel_resolves_it(self):
  calls=[]
  def create(*args):calls.append(1);time.sleep(.04);return object()
  with patch('backend.deferred_services.importlib.import_module',return_value=SimpleNamespace(HardwareMonitor=create)):
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(lambda _:self.f.hardware,range(16)))
  self.assertEqual(len(calls),1);self.assertTrue(all(r is rows[0] for r in rows));self.assertIs(self.f.hilo.resolve('hardware'),rows[0])
 def test_failed_initialization_is_measured_and_retry_is_allowed(self):
  with patch('backend.deferred_services.importlib.import_module',side_effect=ImportError('fixture')):
   with self.assertRaises(ImportError):self.f.binary_tools
  self.assertNotIn('binary_tools',self.f.__dict__);self.assertEqual(self.app.timings.snapshot()['phases'][-1]['status'],'failed')
  self.assertIsNotNone(self.f.binary_tools)
 def test_reference_matches_selected_distribution_and_does_not_claim_behavior(self):
  data=reference(self.f);self.assertEqual(data['sha256'],'f8e18421f1707fb2db6270f3f694dccc083c37b6cc96489c93fb3b6823c759fb')
  self.assertEqual({d['extensions'] for d in data['declarations'] if d['point']=='fileType'},{'n','nm','nb','nbb','ncp','nbo'})
  self.assertTrue(all(d['verification']=='not-tested' for d in data['declarations']))
  self.assertEqual(next(d for d in data['declarations'] if d['point']=='lang.parserDefinition')['mode'],'missing')
 def test_verification_requires_trust_consent_and_local_destination(self):
  service=self.f.language_verification
  with self.assertRaises(PermissionError):service.submit(self.app.workspace,{'language':'c','consent':True})
  self.app.workspace.trusted=True
  with self.assertRaises(PermissionError):service.submit(self.app.workspace,{'language':'c'})
  with patch.object(self.f.execution,'require_local',side_effect=ValueError('remote')):
   with self.assertRaisesRegex(ValueError,'remote'):service.submit(self.app.workspace,{'language':'c','consent':True})
 def test_local_target_does_not_probe_wsl_or_construct_machines(self):
  with patch.object(self.f.execution,'_wsl',return_value=[]) as probe:
   self.f.execution.inventory(self.app.workspace);probe.assert_not_called();self.assertNotIn('machines',self.f.__dict__)
   self.f.execution.inventory(self.app.workspace,True);probe.assert_called_once()
 def test_stale_report_is_not_a_current_verification(self):
  service=self.f.language_verification;service.root.mkdir();(service.root/'c.json').write_text(json.dumps({'signature':'outdated','steps':[]}))
  row=next(r for r in service.snapshot()['languages'] if r['id']=='c');self.assertTrue(row['stale'])
 def test_child_launch_does_not_import_the_desktop_backend(self):
  child=self.root/'probe.py';child.write_text('import sys; assert "backend.server" not in sys.modules; print("CHILD_OK")')
  p=subprocess.run([sys.executable,str(ROOT/'app.py'),'--python-child',str(child)],capture_output=True,text=True,timeout=10)
  self.assertEqual(p.returncode,0,p.stderr);self.assertIn('CHILD_OK',p.stdout)

class MetricPolicyTests(unittest.TestCase):
 def test_nested_spans_keep_their_own_duration_and_report_is_a_copy(self):
  m=StartupMetrics()
  with m.phase('outer'):
   with m.phase('inner'):time.sleep(.002)
  rows=m.snapshot()['phases'];outer=next(r for r in rows if r['name']=='outer');inner=next(r for r in rows if r['name']=='inner')
  self.assertLessEqual(outer['startMs'],inner['startMs']);self.assertGreaterEqual(outer['endMs'],inner['endMs']);rows.clear();self.assertEqual(len(m.snapshot()['phases']),2)
 def test_cpu_policy_does_not_force_the_tcg_cpu_on_whpx(self):
  self.assertEqual(cpu_arguments('whpx'),[]);self.assertEqual(cpu_arguments('kvm'),['-cpu','host']);self.assertEqual(cpu_arguments('tcg'),['-cpu','max'])
 def test_guest_readiness_requires_a_prompt_not_a_window_title_or_progress_message(self):
  from tools.machine_console import console_milestones
  self.assertFalse(console_milestones('Booting zenit@zenit-arch, please wait'))
  self.assertFalse(console_milestones('\x1b]0;zenit@zenit-arch ~ $\x07'))
  self.assertIn(('shell-prompt','shell-ready'),console_milestones('\r\n\x1b]0;zenit@zenit-arch: ~\x07\x1b[32m[zenit@zenit-arch ~]$\x1b[0m '))
 def test_kernel_generic_lazy_factory_is_singleton_and_closing_does_not_resolve(self):
  k=Kernel();calls=[]
  def create():time.sleep(.02);calls.append(1);return object()
  k.register_deferred('lazy',create)
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(lambda _:k.resolve('lazy'),range(12)))
  self.assertEqual(len(calls),1);self.assertTrue(all(r is rows[0] for r in rows))
  k.register_deferred('unused',create);k.stopping=True
  with self.assertRaises(RuntimeError):k.resolve('unused')

if __name__=='__main__':unittest.main()
