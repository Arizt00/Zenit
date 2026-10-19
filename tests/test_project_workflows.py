import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]
class ProjectWorkflowsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.app.workspace.trusted=True;self.flow=self.app.features.workflows;self.ws=self.app.workspace
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def kit(self,lang):
  plan=self.flow.scaffold_plan(self.ws,{'language':lang,'folder':'sample-'+lang});return self.flow.scaffold(self.ws,{'plan':plan['id']})
 def wait(self,task):
  job=self.app.runner.jobs[task['job']];deadline=time.monotonic()+60
  while not job.done and time.monotonic()<deadline:time.sleep(.05)
  self.assertTrue(job.done);self.assertEqual(job.code,0,job.output);return job
 def test_python_plan_real_result_idempotency_and_evidence(self):
  kit=self.kit('python');plan=self.flow.plan(self.ws,{'path':kit['entry'],'action':'run'});task=self.flow.run(self.ws,{'plan':plan['id']});self.assertEqual(self.flow.run(self.ws,{'plan':plan['id']}),task);job=self.wait(task)
  self.assertIn('42',job.output);history=self.flow.history(self.ws);self.assertEqual(history[-1]['state'],'passed')
  packet=self.flow.evidence(self.ws,{'path':kit['entry'],'content':(self.project/kit['entry']).read_text()});self.assertEqual(packet['executions'][-1]['state'],'passed');self.assertIn('42',packet['executions'][-1]['output'])
 def test_check_does_not_execute_python_and_stale_input_rejected(self):
  kit=self.kit('python');file=self.project/kit['entry'];file.write_text('raise RuntimeError("must not execute")\n');plan=self.flow.plan(self.ws,{'path':kit['entry'],'action':'check'});self.wait(self.flow.run(self.ws,{'plan':plan['id']}))
  plan=self.flow.plan(self.ws,{'path':kit['entry'],'action':'run'});file.write_text('print(2)\n')
  with self.assertRaisesRegex(ValueError,'cambiaron'):self.flow.run(self.ws,{'plan':plan['id']})
 def test_scaffolding_never_overwrites_and_paths_bounded(self):
  self.kit('c')
  with self.assertRaises(ValueError):self.flow.scaffold_plan(self.ws,{'language':'c','folder':'sample-c'})
  with self.assertRaises(ValueError):self.flow.scaffold_plan(self.ws,{'language':'c','folder':'../outside'})
  (self.project/'large.c').write_bytes(b'x'*300001)
  with self.assertRaisesRegex(ValueError,'límite'):self.flow.fingerprints(self.ws,'large.c')
 def test_remote_plan_keeps_destination_and_never_substitutes_host_python(self):
  kit=self.kit('python');remote={'commands':[['ssh','fixture','python3','main.py']],'executionTarget':{'id':'ssh:fixture','kind':'ssh','label':'Fixture'}}
  with patch.object(self.app.features.runtimes,'plan',return_value=remote):
   plan=self.flow.plan(self.ws,{'path':kit['entry'],'action':'check'});self.assertEqual(plan['commands'],remote['commands']);self.assertEqual(plan['target']['kind'],'ssh')
 def test_available_native_kits_really_compile_and_run(self):
  for kit in self.flow.catalog(self.ws)['kits']:
   if kit['id']=='python' or not kit['ready']:continue
   with self.subTest(language=kit['id']):
    created=self.kit(kit['id'])
    if created.get('task'):
     self.wait(created['task']);files=list((self.project/created['folder']).rglob('*.n'))+list((self.project/created['folder']).rglob('*.nc'));self.assertTrue(files);entry=files[0].relative_to(self.project).as_posix()
    else:entry=created['entry']
    plan=self.flow.plan(self.ws,{'path':entry,'action':'run'});job=self.wait(self.flow.run(self.ws,{'plan':plan['id']}))
    if kit['id'] not in ('nc','asm'):self.assertIn('42',job.output)

if __name__=='__main__':unittest.main()
