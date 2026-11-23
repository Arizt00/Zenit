import time,unittest
from tests import test_experience_055 as base
from backend.change_footprint import footprint
from backend.version import REVISION

class R2Tests(base.ExperienceTests):
 def test_release_retains_r2_capabilities(self):self.assertGreaterEqual(REVISION,2)
 def test_console_runs_and_checks_an_additional_configured_language(self):
  from backend.runtime_paths import find_tool
  from backend.project_console import dispatch
  python=find_tool('python');self.assertTrue(python);self.source('custom.widget','print("CUSTOM_RUNTIME_OK")\n')
  self.f.runtimes.save({'languages':{'widget':{'extensions':['.widget'],'run':[python,'-u','${file}'],'check':[python,'-c','import sys;compile(open(sys.argv[1]).read(),sys.argv[1],"exec")','${file}']}}})
  result=dispatch(self.f,self.ws,{'command':'run custom.widget'});job=self.job(result);self.assertEqual(job.code,0,job.output);self.assertIn('CUSTOM_RUNTIME_OK',job.stream_output);self.assertEqual(result['language'],'widget');self.assertEqual(self.job(dispatch(self.f,self.ws,{'command':'check custom.widget'})).code,0)
  self.assertIn('widget',[x['id'] for x in self.f.runtimes.status()['languages']])
  with self.assertRaises(ValueError):dispatch(self.f,self.ws,{'command':'build custom.widget'})
  with self.assertRaises(ValueError):self.f.runtimes.save({'languages':{'bad':{'extensions':['.py'],'run':[python,'${file}']}}})
 def test_footprint_follows_imports_and_tests_without_reading_secrets(self):
  self.source('lib/math.py','def add(a,b): return a+b\n');self.source('app.py','from lib.math import add\n');self.source('tests/test_app.py','import app\n');self.source('.env','SECRET=not_to_be_read');self.source('build/generated.py','from lib.math import add\n')
  result=footprint(self.ws,{'path':'lib/math.py','content':'def add(a,b): return a-b\n'})
  self.assertEqual({r['path']:r['depth'] for r in result['affected']},{'app.py':1,'tests/test_app.py':2});self.assertTrue(result['affected'][1]['test']);self.assertTrue(result['changedRanges']);self.assertNotIn('.env',[r['path'] for r in result['consulted']]);self.assertNotIn('build/generated.py',[r['path'] for r in result['consulted']]);self.assertIn('a+b', (self.project/'lib/math.py').read_text())
 def test_footprint_resolves_local_headers_and_handles_incomplete_syntax(self):
  self.source('include/app.h','int add(int,int);\n');self.source('src/main.c','#include "app.h"\nint main(){return 0;}');result=footprint(self.ws,{'path':'include/app.h','content':'long add(long,long);'})
  self.assertEqual(result['affected'][0]['path'],'src/main.c');self.source('broken.py','def incomplete(');self.assertEqual(footprint(self.ws,{'path':'broken.py'})['dependencies'],[])
 def test_matrix_checks_two_real_inputs_without_saving_or_parallel_processes(self):
  file=self.source('main.py','print(int(input())+1)\n');matrix=self.f.lantern_matrix
  plan=matrix.plan(self.ws,{'path':'main.py','content':'print(int(input())+2)\n','cases':[{'stdin':'4\n','expectedOutput':'6\n'},{'stdin':'5\n','expectedOutput':'99\n'}],'timeout':5})
  task=matrix.run(self.ws,{'plan':plan['id']});self.assertEqual(task,matrix.run(self.ws,{'plan':plan['id']}));state=base.wait(self.f.hilo,task['job']);self.assertEqual(state['state'],'done',state);result=state['result'];self.assertEqual(result['passed'],1);self.assertEqual([r['output'].strip() for r in result['cases']],['6','7']);self.assertTrue(result['sequential']);self.assertEqual(file.read_text(),'print(int(input())+1)\n')
 def test_matrix_cancel_does_not_start_next_case(self):
  self.source('main.py','while True: pass\n');matrix=self.f.lantern_matrix;plan=matrix.plan(self.ws,{'path':'main.py','content':'while True: pass\n','cases':[{},{}],'timeout':10});task=matrix.run(self.ws,{'plan':plan['id']});deadline=time.monotonic()+10
  while not any(j.process for j in self.app.runner.jobs.values()) and time.monotonic()<deadline:time.sleep(.02)
  self.f.hilo.cancel(task['job']);self.assertEqual(base.wait(self.f.hilo,task['job'])['state'],'cancelled');self.assertEqual(len(self.app.runner.jobs),1)
 def test_matrix_rejects_invalid_cases_and_compile_failure_cannot_pass(self):
  self.source('bad.c','this does not compile');matrix=self.f.lantern_matrix
  for cases in ([],[{}]*7,[{'expectedExit':True}],[{'stdin':'x'*4097}]):
   with self.assertRaises(ValueError):matrix.plan(self.ws,{'path':'bad.c','content':'broken','cases':cases})
  plan=matrix.plan(self.ws,{'path':'bad.c','content':'this does not compile','cases':[{'expectedExit':1}],'timeout':10});task=matrix.run(self.ws,{'plan':plan['id']});state=base.wait(self.f.hilo,task['job']);self.assertEqual(state['state'],'done',state);self.assertFalse(state['result']['cases'][0]['passed']);self.assertIn('preparación',state['result']['cases'][0]['error'])
 def test_lantern_comparison_uses_recorded_hashes_and_starts_no_process(self):
  self.source('main.py','print("first")\n');self.f.lantern.start(self.ws,'main.py','print("first")\n',1)
  def completed(version):
   deadline=time.monotonic()+15
   while time.monotonic()<deadline:
    state=self.f.lantern.snapshot()
    if state.get('bufferVersion')==version and state.get('executedGeneration')==state.get('generation') and state.get('code') is not None:return
    time.sleep(.04)
   self.fail(str(state))
  completed(1);self.f.lantern.buffer(self.ws,'main.py','print("second")\n',2);completed(2);self.f.lantern.stop();count=len(self.app.runner.jobs);result=self.f.lantern.compare(self.ws,{})
  self.assertFalse(result['equivalent']);self.assertIn('second',result['diff']);self.assertNotEqual(result['before']['sourceSha256'],result['after']['sourceSha256']);self.assertEqual(len(self.app.runner.jobs),count)
  self.f.lantern.history[0].pop('outputSha256');self.assertIsNone(self.f.lantern.compare(self.ws,{})['equivalent'])

if __name__=='__main__':unittest.main()
