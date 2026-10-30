import importlib.util,json,time,unittest
from pathlib import Path
from tests.test_experience_055 import ExperienceTests
from backend.lantern_matrix import LanternMatrix
from backend.melody_dossier import dossier
from backend.lantern import Lantern

class ReinforcementTests(ExperienceTests):
 def complete(self,version):
  end=time.monotonic()+20
  while time.monotonic()<end:
   state=self.f.lantern.snapshot()
   if state.get('bufferVersion')==version and state.get('executedGeneration')==state.get('generation') and state.get('code') is not None:return state
   time.sleep(.03)
  self.fail(str(state))
 def test_cases_are_restored_by_file_after_service_recreation_without_execution(self):
  source=self.source('main.py','print(input())\n');self.source('other.py','print(0)\n');matrix=self.f.lantern_matrix
  body={'path':'main.py','timeout':5,'cases':[{'name':'Español','stdin':'niño\n','expectedOutput':'niño\n'},{'name':'Segundo','expectedExit':2}]}
  result=matrix.save_cases(self.ws,body);self.assertEqual(result['cases'][0]['stdin'],'niño\n');restored=LanternMatrix(self.f).saved_cases(self.ws,'main.py');self.assertEqual(restored,result);self.assertFalse(matrix.saved_cases(self.ws,'other.py')['saved']);self.assertEqual(len(self.app.runner.jobs),0);self.assertEqual(source.read_text(),'print(input())\n')
  with self.assertRaises(ValueError):matrix.save_cases(self.ws,{**body,'cases':[{}]*7})
  self.ws.trusted=False
  with self.assertRaises(PermissionError):matrix.saved_cases(self.ws,'main.py')
 def test_baseline_detects_output_regression_and_survives_restart(self):
  source=self.source('main.py','print("reference")\n');lantern=self.f.lantern
  lantern.start(self.ws,'main.py','print("reference")\n',1);self.complete(1);baseline=lantern.set_baseline(self.ws,{'path':'main.py'})['baseline'];self.assertEqual(baseline['code'],0)
  lantern.buffer(self.ws,'main.py','print("different")\n',2);state=self.complete(2);self.assertEqual(state['baselineVerification']['status'],'failed');lantern.stop()
  restored=Lantern(self.f.runtimes,self.app.runner,self.f.preview);self.assertEqual(restored.get_baseline(self.ws,'main.py'),baseline)
  lantern.start(self.ws,'main.py','print("reference")\n',3);self.assertEqual(self.complete(3)['baselineVerification']['status'],'passed');self.assertEqual(source.read_text(),'print("reference")\n')
  lantern.set_baseline(self.ws,{'path':'main.py','clear':True});self.assertIsNone(lantern.get_baseline(self.ws,'main.py'))
 def test_baseline_with_changed_input_is_not_reported_as_regression(self):
  self.source('main.py','print(input())\n');lantern=self.f.lantern
  options={'inputEnabled':True,'stdin':'one\n','closeInput':True};lantern.configure(self.ws,{'path':'main.py','options':options});lantern.start(self.ws,'main.py','print(input())\n',1);self.complete(1);lantern.set_baseline(self.ws,{'path':'main.py'})
  lantern.configure(self.ws,{'path':'main.py','options':{**options,'stdin':'two\n'}});lantern.buffer(self.ws,'main.py','print(input()) # changed\n',2);self.assertEqual(self.complete(2)['baselineVerification']['status'],'differentInput')
 def test_cannot_pin_an_obsolete_buffer_or_cancelled_execution(self):
  self.source('main.py','print(1)\n');lantern=self.f.lantern;lantern.start(self.ws,'main.py','print(1)\n',1);self.complete(1);lantern.buffer(self.ws,'main.py','while True: pass\n',2)
  with self.assertRaises(ValueError):lantern.set_baseline(self.ws,{'path':'main.py'})
  lantern.stop()
 def test_dossier_marks_old_execution_and_excludes_other_files_and_secrets(self):
  self.source('helper.py','VALUE=7\n');self.source('main.py','from helper import VALUE\nprint(VALUE)\n');self.source('.env','MUST_NOT_LEAK=secret')
  lantern=self.f.lantern;lantern.start(self.ws,'main.py','from helper import VALUE\nprint(VALUE)\n',1);self.complete(1)
  report=dossier(self.f,self.ws,{'path':'main.py','content':'from helper import VALUE\nprint(VALUE+1)\n','diagnostics':[{'message':'example','source':'compiler'}]})
  self.assertFalse(report['execution']['matchesBuffer']);self.assertEqual({r['path'] for r in report['sources']},{'main.py','helper.py'});self.assertNotIn('MUST_NOT_LEAK',json.dumps(report));self.assertTrue(report['diff']);self.assertEqual(report['diagnostics'][0]['message'],'example')
  self.source('other.py','print("other")\n');self.assertIsNone(dossier(self.f,self.ws,{'path':'other.py'})['execution'])
 def test_local_nc_extension_patch_uses_process_arguments(self):
  path=Path(__file__).resolve().parents[1]/'integrations/nc-language/terminal-fix.py';spec=importlib.util.spec_from_file_location('nc_fix',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.assertIn('options.shellPath = resolved.nccPath',module.TERMINAL_FUNCTION);self.assertIn('options.shellArgs = argv.map',module.TERMINAL_FUNCTION)

if __name__=='__main__':unittest.main()
