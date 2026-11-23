import copy,json,threading,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_experience_055 import ExperienceTests
from tests.test_hilo_tern import wait
from backend.execution_readiness import inspect
from backend.hilo import Hilo
from backend.lantern_adapters import prepare

class ClosureTests(ExperienceTests):
 def wsl(self):
  target={'id':'wsl:Fixture','label':'WSL · Fixture','kind':'wsl','distribution':'Fixture','executable':'wsl.exe','available':True,'system':'linux'}
  self.f.workbenches.set_target(self.ws,target['id'],{})
  self.addCleanup(patch.stopall)
  patch.object(self.f.execution,'inventory',return_value={'targets':[target]}).start()
  return target
 def test_reviewed_wsl_plan_binds_target_and_rejects_a_changed_destination(self):
  self.source('main.py','print(1)');target=self.wsl()
  plan=self.f.countercheck.plan(self.ws,{'path':'main.py','content':'print(2)'})
  self.assertEqual(plan['executionTarget']['id'],target['id']);self.f.workbenches.set_target(self.ws,'local',{})
  with self.assertRaisesRegex(ValueError,'destino'):self.f.countercheck.run(self.ws,{'plan':plan['id']})
 def test_remote_java_nc_and_custom_language_build_plans_never_execute_when_building(self):
  self.source('Main.java','package sample; public class Main { public static void main(String[] a) {} }');self.source('main.n','hello {}');self.source('main.lua','print(1)');self.wsl()
  self.f.runtimes.config['languages']['lua']={'extensions':['.lua'],'build':['luac','-o','${target}','${file}'],'run':['lua','${target}']}
  for path,tool in [('Main.java','javac'),('main.n','ncc'),('main.lua','luac')]:
   plan=self.f.runtimes.plan(self.ws,path,build_only=True)
   self.assertEqual(len(plan['commands']),1);self.assertIn(tool,plan['commands'][0][-1]);self.assertNotIn('&& exec java ',plan['commands'][0][-1]);self.assertEqual(plan['language'],{'Main.java':'java','main.n':'nc','main.lua':'lua'}[path])
  self.assertIn('sample.Main',self.f.runtimes.plan(self.ws,'Main.java')['commands'][-1][-1])
 def test_remote_preparation_does_not_launch_a_windows_memory_adapter(self):
  self.source('main.py','print(1)');self.wsl();plan=prepare(self.f.runtimes,self.ws,'main.py')
  self.assertTrue(plan['custom']);self.assertEqual(plan['checks'][0][0],'wsl.exe');self.assertIn('py_compile',plan['checks'][0][-1]);self.assertIn('python3 -u',plan['commands'][0][-1]);self.assertEqual(plan['language'],'python')
 def test_tool_readiness_reports_the_actual_target_and_missing_tools_without_running_project(self):
  self.source('Main.java','class Main {}');self.wsl()
  from types import SimpleNamespace
  with patch('backend.execution_readiness.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='0\t/usr/bin/javac\n1\t\n',stderr='')) as run:
   result=inspect(self.f,self.ws,'Main.java',threading.Event())
  self.assertFalse(result['ready']);self.assertEqual([r['available'] for r in result['tools']],[True,False]);self.assertIn('command -v',run.call_args.args[0][-1]);self.assertEqual(len(self.app.runner.jobs),0)
 def test_dossier_includes_destination_and_language_without_claiming_runtime_readiness(self):
  self.source('main.n','hello {}');self.wsl()
  from backend.melody_dossier import dossier
  result=dossier(self.f,self.ws,{'path':'main.n'});self.assertEqual(result['environment']['language'],'nc');self.assertEqual(result['environment']['target']['id'],'wsl:Fixture');self.assertIn('no confirma',result['environment']['note'])
 def test_language_status_requires_both_java_tools_and_checks_custom_executable(self):
  self.f.runtimes.config['languages']['lua']={'extensions':['.lua'],'run':['missing-lua','${file}']}
  with patch('backend.runtimes.find_tool',side_effect=lambda name,*a:'javac' if name=='javac' else None):
   rows={r['id']:r for r in self.f.runtimes.status()['languages']}
  self.assertFalse(rows['java']['available']);self.assertFalse(rows['lua']['available'])

class SchedulerResilienceTests(unittest.TestCase):
 def test_failed_cancellation_cleanup_does_not_kill_worker_or_strand_dependents(self):
  core=Hilo(None);gate=threading.Event();started=threading.Event()
  def broken():raise ValueError('adapter cleanup failed')
  try:
   core.submit('Gate',lambda event:(started.set(),gate.wait(4)));self.assertTrue(started.wait(2))
   first=core.submit('Cancelled',lambda event:self.fail('cancelled operation ran'),workspace='project',cancel=broken)
   child=core.submit('Dependent',lambda event:self.fail('dependent ran'),workspace='project',depends=[first['job']],cancel=broken)
   core.cancel(first['job']);gate.set();self.assertEqual(wait(core,child['job'])['state'],'cancelled')
   healthy=core.submit('Healthy',lambda event:42);self.assertEqual(wait(core,healthy['job'])['result'],42);self.assertTrue(core.worker.is_alive());self.assertIn('cleanupError',wait(core,first['job']))
  finally:gate.set();core.shutdown()

if __name__=='__main__':unittest.main()
