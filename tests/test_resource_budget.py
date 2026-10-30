import json,os,sys,tempfile,time,unittest
from pathlib import Path
import psutil
from backend.server import Application
ROOT=Path(__file__).resolve().parents[1]

class ResourceBudgetTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.root/'profile');self.f=self.app.features;self.budget=self.f.hilo.budget
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def wait(self,predicate,seconds=10):
  deadline=time.monotonic()+seconds
  while not predicate() and time.monotonic()<deadline:time.sleep(.03)
  self.assertTrue(predicate())
 def program(self,code,background=False):
  task=self.app.runner.start([[sys.executable,'-u','-c',code]],self.project,resource_class='background' if background else 'foreground');return self.app.runner.jobs[task['job']]
 def test_no_sampler_until_a_tool_runs_and_idle_sampler_exits(self):
  self.assertIsNone(self.budget.thread);job=self.program('print(42)');self.wait(lambda:job.done);self.wait(lambda:not self.budget.entries);self.wait(lambda:not self.budget.thread or not self.budget.thread.is_alive())
 def test_cpu_pool_changes_only_registered_tool_not_editor(self):
  if not hasattr(psutil.Process(),'cpu_affinity'):self.skipTest('CPU affinity unsupported')
  original=psutil.Process().cpu_affinity();self.f.prefs.update({'hardware.toolCores':1})
  job=self.program('import psutil,json,time;time.sleep(.3);print(json.dumps(psutil.Process().cpu_affinity()))');self.wait(lambda:job.done)
  self.assertEqual(json.loads(job.stream_output.strip()),original[:1]);self.assertEqual(psutil.Process().cpu_affinity(),original)
 def test_cancel_removes_tracked_descendants_even_when_root_is_killed(self):
  code='import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);print(p.pid,flush=True);time.sleep(30)'
  job=self.program(code);self.wait(lambda:job.stream_output.strip().isdigit());pid=int(job.stream_output.strip())
  self.wait(lambda:pid in self.budget.entries.get(job.id,{}).get('known',{}));job.cancel();self.wait(lambda:job.done)
  self.wait(lambda:not psutil.pid_exists(pid) or psutil.Process(pid).status()==psutil.STATUS_ZOMBIE)
 def test_aggregate_memory_budget_prefers_stopping_background_tool(self):
  self.f.prefs.update({'hardware.toolMemoryMB':256})
  code='import time; value=bytearray(150*1024*1024);print("ready",flush=True);time.sleep(15)'
  foreground=self.program(code);self.wait(lambda:'ready' in foreground.stream_output)
  background=self.program(code,True);self.wait(lambda:background.done)
  self.assertTrue(background.cancelled);self.assertIn('presupuesto global',background.output);self.assertFalse(foreground.cancelled);foreground.cancel()
 def test_cpu_preference_updates_a_running_tool_without_changing_editor(self):
  if not hasattr(psutil.Process(),'cpu_affinity') or len(psutil.Process().cpu_affinity())<2:self.skipTest('Two CPU cores required')
  original=psutil.Process().cpu_affinity();self.f.prefs.update({'hardware.toolCores':2})
  job=self.program('import time;print("ready",flush=True);time.sleep(10)');self.wait(lambda:'ready' in job.stream_output);self.f.prefs.update({'hardware.toolCores':1});self.wait(lambda:psutil.Process(job.process.pid).cpu_affinity()==original[:1]);self.assertEqual(psutil.Process().cpu_affinity(),original);job.cancel()
 def test_idle_snapshot_drops_stale_usage_and_reports_current_limits(self):
  job=self.program('import time;value=bytearray(10*1024*1024);print("ready",flush=True);time.sleep(.6)');self.wait(lambda:self.budget.snapshot().get('rssBytes',0)>0);self.wait(lambda:job.done);self.wait(lambda:not self.budget.thread or not self.budget.thread.is_alive())
  self.f.prefs.update({'hardware.toolCores':1,'hardware.toolMemoryMB':512});state=self.budget.snapshot();self.assertEqual(state['rssBytes'],0);self.assertEqual(state['cores'],1);self.assertEqual(state['memoryBytes'],512*1024**2)

if __name__=='__main__':unittest.main()
