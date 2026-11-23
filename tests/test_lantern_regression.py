import json,tempfile,threading,time,unittest
from pathlib import Path
from backend.server import Application
from backend.execution_evidence import context,runtime_signature
from backend.melody_countercheck import digest
from backend.preferences import atomic_json
from tests.test_hilo_tern import wait

ROOT=Path(__file__).resolve().parents[1]

class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.ws=self.base/'project';self.ws.mkdir();self.path='main.py';(self.ws/self.path).write_text('print(42)\n');self.app=Application(ROOT,self.ws,data_dir=self.base/'profile');self.app.workspace.trusted=True;self.engine=self.app.features.lantern_regression
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def history(self,sources):
        directory=self.app.workspace.private_dir('lantern')/digest(self.path)[:24];directory.mkdir(parents=True,exist_ok=True);rows=[]
        for revision,source in enumerate(sources,1):
            atomic_json(directory/f'replay-{revision}.json',{'source':source,'sourceSha256':digest(source)})
            rows.append({'path':self.path,'revision':revision,'replayAvailable':True,'sourceSha256':digest(source),'context':context(self.app.workspace,self.path,source),'runtimeSha256':runtime_signature(self.app.features.runtimes),'environment':None})
        atomic_json(directory/'history.json',rows)
    def run_plan(self,**data):
        plan=self.engine.plan(self.app.workspace,{'path':self.path,**data});task=self.engine.run(self.app.workspace,{'plan':plan['id']});job=wait(self.app.features.hilo,task['job'],90);self.assertEqual(job['state'],'done',job);return job['result']
    def test_first_changed_revision_is_replayed_twice_even_when_a_later_revision_recovers(self):
        self.history(['print(42)\n','print(42)\n','print(0)\n','print(42)\n']);original=(self.ws/self.path).read_bytes()
        result=self.run_plan(mode='first-change');self.assertEqual(result['firstChangedRevision'],3);self.assertEqual(result['status'],'changed');self.assertEqual(len(result['trials']),8);self.assertEqual([r['different'] for r in result['observations']],[False,False,True,False]);self.assertEqual((self.ws/self.path).read_bytes(),original)
    def test_unstable_outputs_and_changed_dependencies_prevent_attribution(self):
        self.history(['print(42)\n','import time\nprint(time.time_ns())\n']);result=self.run_plan(mode='first-change');self.assertEqual(result['status'],'unstable');self.assertIsNone(result['firstChangedRevision'])
        (self.ws/'helper.py').write_text('VALUE=1\n');self.history(['from helper import VALUE\nprint(VALUE)\n','from helper import VALUE\nprint(VALUE+1)\n']);(self.ws/'helper.py').write_text('VALUE=2\n')
        with self.assertRaisesRegex(ValueError,'contexto'):self.engine.plan(self.app.workspace,{'path':self.path,'mode':'first-change'})
    def test_reduction_keeps_the_same_failure_and_preserves_original_source(self):
        source='import sys\ntext=sys.stdin.read()\nprint("BUG" if "!" in text else "OK")\n';(self.ws/self.path).write_text(source)
        result=self.run_plan(mode='reduce-input',content=source,stdin='unnecessary ! characters',expectedOutput='OK\n',expectedExit=0)
        self.assertIn(result['status'],('reduced','budget'));self.assertIn('!',result['reducedInput']);self.assertLess(result['reducedInputBytes'],result['originalInputBytes']);self.assertEqual((self.ws/self.path).read_text(),source);self.assertLessEqual(len(result['trials']),32)
        failing={r['outputSha256'] for r in result['trials'] if r['output']=='BUG\n'};self.assertEqual(len(failing),1)
    def test_not_failing_and_cancelled_do_not_fabricate_a_reduction(self):
        result=self.run_plan(mode='reduce-input',stdin='anything',expectedOutput='42\n');self.assertEqual(result['status'],'not-failing');self.assertEqual(len(result['trials']),2)
        plan=self.engine.plan(self.app.workspace,{'path':self.path,'mode':'reduce-input','stdin':'input','expectedOutput':'wrong'})
        event=threading.Event();event.set()
        from concurrent.futures import CancelledError
        with self.assertRaises(CancelledError):self.engine.execute(self.app.workspace,self.engine.plans[plan['id']],event)

    def test_completed_history_is_immediately_available_and_reference_updates_do_not_rewrite_sources(self):
        live=self.app.features.lantern;live.start(self.app.workspace,self.path,'print(42)\n',1);deadline=time.monotonic()+25
        while not (live.job and live.job.done) and time.monotonic()<deadline:time.sleep(.04)
        self.assertTrue(live.job and live.job.done);state=live.snapshot();self.assertEqual(len(state['history']),1);self.assertTrue(state['history'][0]['replayAvailable']);file=live.memory_dir/f'replay-{live.revision}.json';stamp=file.stat().st_mtime_ns
        live.set_baseline(self.app.workspace,{'path':self.path});self.assertEqual(live.snapshot()['history'][0]['baselineVerification']['status'],'passed')
        live.set_baseline(self.app.workspace,{'path':self.path,'clear':True});self.assertEqual(live.snapshot()['history'][0]['baselineVerification']['status'],'off');self.assertEqual(file.stat().st_mtime_ns,stamp);self.assertEqual(len(live.history),1)

if __name__=='__main__':unittest.main()
