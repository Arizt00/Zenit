import json,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.execution_evidence import runtime_signature

ROOT=Path(__file__).resolve().parents[1]

class InvestigationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.base=Path(self.temp.name);self.root=self.base/'project';self.root.mkdir()
  self.write('calc.py','def answer():\n return 42\n')
  self.write('main.py','import calc\nprint(calc.answer())\n')
  self.write('test_calc.py','import unittest,calc\nclass Check(unittest.TestCase):\n def test_answer(self): self.assertEqual(calc.answer(),42)\n')
  self.app=Application(ROOT,self.root,data_dir=self.base/'profile');self.f=self.app.features;self.ws=self.app.workspace;self.ws.trusted=True;self.research=self.f.investigations
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def write(self,path,text):
  file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8')
 def wait(self,task):
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   row=self.f.hilo.jobs[task['job']]
   if row['state'] in ('done','failed','cancelled'):return row
   time.sleep(.03)
  self.fail('Task timed out')
 def test_capture_is_read_only_and_keeps_old_sources_after_edits(self):
  r=self.research.create(self.ws,{'path':'main.py','question':'What changed?'})
  self.assertFalse(self.app.runner.jobs);self.assertEqual(len(r['chain']),7)
  self.write('calc.py','def answer():\n return 0\n')
  old=self.research.snapshot(self.ws,r['snapshot']);self.assertIn('42',old['sources']['calc.py']['content'])
  self.assertTrue(next(x for x in self.research.describe(self.ws,r)['sources'] if x['path']=='calc.py')['changed'])
 def test_actual_failed_test_links_baseline_replays_old_revision_and_verifies_proposal(self):
  first=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.assertEqual(self.wait(first)['state'],'done')
  self.write('calc.py','def answer():\n return 0\n')
  failed=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.assertEqual(self.wait(failed)['state'],'failed')
  r=self.research.create(self.ws,{'path':'test_calc.py','originKind':'test','originId':failed['run'],'question':'This used to pass'})
  self.assertEqual(r['baseline']['id'],first['run']);self.assertEqual(r['changesSinceBaseline'][0]['path'],'calc.py')
  self.write('calc.py','def answer():\n return 99\n')
  for variant,expected in [('baseline',0),('captured',1)]:
   plan=self.research.replay_plan(self.ws,{'id':r['id'],'variant':variant});task=self.research.run(self.ws,{'plan':plan['id'],'consent':True});self.assertEqual(self.research.run(self.ws,{'plan':plan['id'],'consent':True}),task)
   state=self.wait(task);self.assertEqual(state['state'],'done',state.get('error'));trial=state['result']['trials'][-1]
   self.assertEqual([x['code'] for x in trial['runs']],[expected,expected]);self.assertTrue(trial['stable'],trial)
  proposal=self.research.proposal(self.ws,{'id':r['id'],'proposal':{'interpretation':'Candidate correction, not yet verified.','changes':[{'path':'calc.py','content':'def answer():\n return 42\n'}]}})
  changes=[{k:c[k] for k in ('path','before','after')} for c in proposal['proposal']['changes']]
  plan=self.research.replay_plan(self.ws,{'id':r['id'],'changes':changes});state=self.wait(self.research.run(self.ws,{'plan':plan['id'],'consent':True}));self.assertEqual(state['state'],'done',state.get('error'))
  self.assertTrue(all(x['tests']['summary']['passed']==1 for x in state['result']['trials'][-1]['runs']))
  self.assertIn('99',(self.root/'calc.py').read_text());self.assertEqual(len(self.research.listing(self.ws)['investigations']),1)
 def test_historical_result_without_sources_is_not_claimed_as_current(self):
  run=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.wait(run);self.f.tests.runs[run['run']].pop('evidence')
  r=self.research.create(self.ws,{'path':'test_calc.py','originKind':'test','originId':run['run']})
  self.assertTrue(any('histórico' in text for text in r['missing']))
 def test_changed_data_and_environment_reject_replay_without_running(self):
  self.write('input.txt','before');r=self.research.create(self.ws,{'path':'main.py'})
  self.write('input.txt','after')
  with self.assertRaisesRegex(ValueError,'datos'):self.research.replay_plan(self.ws,{'id':r['id']})
  self.write('input.txt','before');self.f.runtimes.config['languages'].setdefault('python',{})['run']=['different']
  with self.assertRaisesRegex(ValueError,'entorno'):self.research.replay_plan(self.ws,{'id':r['id']})
  self.assertFalse(self.app.runner.jobs)
 def test_data_changed_after_command_review_is_rejected_at_execution(self):
  self.write('input.txt','one');r=self.research.create(self.ws,{'path':'main.py'});p=self.research.replay_plan(self.ws,{'id':r['id']});self.write('input.txt','two')
  state=self.wait(self.research.run(self.ws,{'plan':p['id'],'consent':True}));self.assertEqual(state['state'],'failed');self.assertFalse(self.app.runner.jobs)
 def test_model_cannot_introduce_unreviewed_files_or_commands(self):
  r=self.research.create(self.ws,{'path':'main.py'})
  for path in ['../outside.py','.env','new.py','.lumen/config.py']:
   with self.subTest(path=path),self.assertRaises(ValueError):self.research.proposal(self.ws,{'id':r['id'],'proposal':{'changes':[{'path':path,'content':'bad'}]}})
  self.assertFalse(self.app.runner.jobs)
 def test_proposal_contains_independently_selectable_fragments(self):
  self.write('main.py','a=1\n\nprint(a)\n\nb=2\n')
  r=self.research.create(self.ws,{'path':'main.py'});r=self.research.proposal(self.ws,{'id':r['id'],'proposal':json.dumps({'interpretation':'Two edits','changes':[{'path':'main.py','content':'a=3\n\nprint(a)\n\nb=4\n'}]})})
  self.assertEqual(len(r['proposal']['changes'][0]['hunks']),2);self.assertEqual((self.root/'main.py').read_text(),'a=1\n\nprint(a)\n\nb=2\n')
 def test_prompt_uses_only_explicitly_selected_sources_and_separates_claims(self):
  self.write('.env','SECRET=keep-local');r=self.research.create(self.ws,{'path':'main.py'})
  request=self.research.prompt(self.ws,{'id':r['id'],'paths':['main.py']});prompt=request['question']+request['context'];self.assertIn('no una causa demostrada',prompt);self.assertNotIn('SECRET',prompt);self.assertNotIn('def answer',prompt);self.assertLessEqual(len(request['context']),64000);self.assertLessEqual(len(request['question']),24000)
  with self.assertRaises(ValueError):self.research.prompt(self.ws,{'id':r['id'],'paths':['.env']})
 def test_snapshot_tampering_and_foreign_identifiers_are_rejected(self):
  r=self.research.create(self.ws,{'path':'main.py'});file=self.research.folder(self.ws)/('snapshot-'+r['snapshot']+'.json');value=json.loads(file.read_text());value['sources']['main.py']['content']='changed';file.write_text(json.dumps(value))
  with self.assertRaisesRegex(ValueError,'modificada'):self.research.describe(self.ws,r)
  for identity in ['../outside','0'*32]:
   with self.assertRaises(ValueError):self.research.get(self.ws,identity)
 def test_native_compilation_replay_keeps_generated_files_inside_the_copy(self):
  from backend.runtime_paths import find_tool
  if not find_tool('gcc'):self.skipTest('GCC unavailable')
  self.write('native.c','#include <stdio.h>\nint main(void){puts("native research");return 0;}\n')
  r=self.research.create(self.ws,{'path':'native.c'});plan=self.research.replay_plan(self.ws,{'id':r['id']});state=self.wait(self.research.run(self.ws,{'plan':plan['id'],'consent':True}))
  self.assertEqual(state['state'],'done',state.get('error'));self.assertTrue(state['result']['trials'][-1]['stable']);self.assertFalse((self.root/'CMakeLists.txt').exists());self.assertTrue(all('native research' in t['output'] for t in state['result']['trials'][-1]['runs']))
 def test_emoji_comments_keep_fragment_offsets_compatible_with_editor_utf16(self):
  self.write('main.py','# 😀\na=1\n');r=self.research.create(self.ws,{'path':'main.py'});r=self.research.proposal(self.ws,{'id':r['id'],'proposal':{'changes':[{'path':'main.py','content':'# 😀\na=2\n'}]}})
  h=r['proposal']['changes'][0]['hunks'][0];self.assertEqual(h['start'],5);self.assertEqual(h['before'],'a=1\n')
 def test_finished_terminal_output_has_the_source_identity_of_its_run(self):
  reply=self.f.hacker.start(self.ws,'main.py',(self.root/'main.py').read_text(),'file');session=self.f.terminals.get(reply['terminal']['id']);deadline=time.monotonic()+10
  while not session.closed and time.monotonic()<deadline:time.sleep(.03)
  self.assertTrue(session.closed);self.write('main.py','print("changed later")\n')
  r=self.research.create(self.ws,{'path':'main.py','originKind':'terminal','originId':session.id});self.assertIn('42',r['origin']['output']);self.assertIn('calc.answer',self.research.snapshot(self.ws,r['snapshot'])['sources']['main.py']['content']);self.assertTrue(any('entrada interactiva' in x for x in r['missing']))
 def test_investigation_protects_sources_against_unrelated_capture_eviction(self):
  r=self.research.create(self.ws,{'path':'main.py'})
  for i in range(26):self.write('calc.py','value='+str(i)+'\n');self.research.capture(self.ws)
  self.assertIn('answer',self.research.snapshot(self.ws,r['snapshot'])['sources']['calc.py']['content'])
 def test_program_modifying_its_own_source_does_not_produce_verified_evidence(self):
  self.write('main.py','from pathlib import Path\nPath(__file__).write_text("print(2)")\nprint(1)\n')
  r=self.research.create(self.ws,{'path':'main.py'});p=self.research.replay_plan(self.ws,{'id':r['id']});state=self.wait(self.research.run(self.ws,{'plan':p['id'],'consent':True}));self.assertEqual(state['state'],'done',state.get('error'))
  trial=state['result']['trials'][-1];self.assertFalse(trial['stable']);self.assertTrue(all('main.py' in run['sourcesChangedDuringRun'] for run in trial['runs']));self.assertIn('write_text',(self.root/'main.py').read_text())
 def test_build_result_replay_does_not_turn_into_program_execution(self):
  self.write('main.py','from pathlib import Path\nPath("must-not-exist.txt").write_text("executed")\n')
  plan=self.f.workflows.plan(self.ws,{'path':'main.py','action':'build'});task=self.f.workflows.run(self.ws,{'plan':plan['id']});job=self.app.runner.jobs[task['job']];deadline=time.monotonic()+10
  while not job.done and time.monotonic()<deadline:time.sleep(.03)
  self.assertTrue(job.done);r=self.research.create(self.ws,{'path':'main.py','originKind':'workflow','originId':job.id});self.assertEqual(r['action'],'build')
  p=self.research.replay_plan(self.ws,{'id':r['id']});self.assertTrue(any('py_compile' in str(argv) for argv in p['commands']));state=self.wait(self.research.run(self.ws,{'plan':p['id'],'consent':True}));self.assertEqual(state['state'],'done',state.get('error'));self.assertFalse((self.root/'must-not-exist.txt').exists())
 def test_adapter_change_after_review_stops_reproduction_before_spawning(self):
  helper=self.base/'adapter.py';helper.write_text('import runpy,sys\nrunpy.run_path(sys.argv[1])\n')
  self.f.runtimes.config['languages']['python']={'run':[__import__('sys').executable,str(helper),'${file}'],'check':[__import__('sys').executable,'-c','pass']}
  r=self.research.create(self.ws,{'path':'main.py'});p=self.research.replay_plan(self.ws,{'id':r['id']});helper.write_text(helper.read_text()+'\n# changed\n');state=self.wait(self.research.run(self.ws,{'plan':p['id'],'consent':True}));self.assertEqual(state['state'],'failed');self.assertIn('herramienta',state['error']);self.assertFalse(self.app.runner.jobs)
 def test_bounded_saved_test_extract_keeps_full_behavior_comparison(self):
  from unittest.mock import patch
  run=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.wait(run)
  r=self.research.create(self.ws,{'path':'test_calc.py','originKind':'test','originId':run['run']});p=self.research.replay_plan(self.ws,{'id':r['id']});read=self.f.tests.read_result;calls=[]
  def reported(*args):
   result=read(*args);calls.append(1);result['results']=[{'id':str(i),'status':'passed','message':('different '+str(len(calls))) if i==50 else 'same'} for i in range(51)];return result
  with patch.object(self.f.tests,'read_result',side_effect=reported):state=self.wait(self.research.run(self.ws,{'plan':p['id'],'consent':True}))
  self.assertEqual(state['state'],'done',state.get('error'));trial=state['result']['trials'][-1];self.assertFalse(trial['stable']);self.assertTrue(all(t['tests']['resultsLimited'] and len(t['tests']['results'])==50 for t in trial['runs']));self.assertNotEqual(trial['runs'][0]['behaviorSha256'],trial['runs'][1]['behaviorSha256'])
 def test_record_budget_rejection_preserves_previous_persisted_record(self):
  r=self.research.create(self.ws,{'path':'main.py'});record=self.research.get(self.ws,r['id']);record['question']='x'*(4*1024**2)
  with self.assertRaisesRegex(ValueError,'4 MiB'):self.research.save(self.ws,record)
  self.assertNotEqual(self.research.get(self.ws,r['id'])['question'],record['question'])
 def test_passing_run_from_a_different_suite_directory_is_not_a_baseline(self):
  first=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.wait(first);self.f.tests.runs[first['run']]['plan']['directory']='other-tests'
  self.write('calc.py','def answer():\n return 0\n');failed=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.wait(failed)
  r=self.research.create(self.ws,{'path':'test_calc.py','originKind':'test','originId':failed['run']});self.assertIsNone(r['baseline']);self.assertTrue(any('No se ha encontrado' in x for x in r['missing']))
 def test_expired_historical_snapshot_allows_explicit_new_revision_without_false_attribution(self):
  run=self.f.tests.start(self.ws,{'framework':'unittest','consent':True});self.wait(run);identity=self.f.tests.runs[run['run']]['evidence']['snapshot'];(self.research.folder(self.ws)/('snapshot-'+identity+'.json')).unlink()
  self.write('calc.py','def answer():\n return 0\n');r=self.research.create(self.ws,{'path':'test_calc.py','originKind':'test','originId':run['run']})
  self.assertNotEqual(r['snapshot'],identity);self.assertIsNone(r['baseline']);self.assertTrue(any('ya no está disponible' in x for x in r['missing']));self.assertEqual(r['origin']['result']['summary']['passed'],1);self.assertIn('return 0',self.research.snapshot(self.ws,r['snapshot'])['sources']['calc.py']['content'])
 def test_finishing_replay_preserves_a_proposal_received_while_it_was_running(self):
  self.write('main.py','import time\ntime.sleep(.5)\nprint(42)\n');r=self.research.create(self.ws,{'path':'main.py'});p=self.research.replay_plan(self.ws,{'id':r['id']});task=self.research.run(self.ws,{'plan':p['id'],'consent':True});deadline=time.monotonic()+10
  while not self.app.runner.jobs and time.monotonic()<deadline:time.sleep(.01)
  self.assertTrue(self.app.runner.jobs);proposal=self.research.proposal(self.ws,{'id':r['id'],'proposal':{'interpretation':'New hypothesis received during the experiment','changes':[{'path':'main.py','content':'print(43)\n'}]}})
  state=self.wait(task);self.assertEqual(state['state'],'done',state.get('error'));saved=self.research.get(self.ws,r['id']);self.assertEqual(saved['proposal']['id'],proposal['proposal']['id']);self.assertEqual(len(saved['trials']),1)

if __name__=='__main__':unittest.main()
