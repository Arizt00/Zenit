import json,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from tests.test_hilo_tern import wait

ROOT=Path(__file__).resolve().parents[1]
class ProjectTestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();(self.project/'tests').mkdir();(self.project/'calc.py').write_text('def total():\n    return 42\n')
        (self.project/'tests/test_calc.py').write_text('import unittest,time\nfrom calc import total\nclass CalcTests(unittest.TestCase):\n def test_ok(self):\n  time.sleep(.3)\n  self.assertEqual(total(),42)\n def test_failure(self):\n  self.assertEqual(total(),41)\n')
        self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.app.workspace.trusted=True
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def test_discovery_does_not_import_and_real_results_link_to_failure_line(self):
        manager=self.app.features.tests;ws=self.app.workspace;inventory=manager.discover(ws)
        self.assertEqual(len(inventory['tests']),2);self.assertFalse(self.app.runner.jobs)
        run=manager.start(ws,{'framework':'unittest','consent':True});duplicate=manager.start(ws,{'framework':'unittest','consent':True});self.assertEqual(run['job'],duplicate['job'])
        job=wait(self.app.features.hilo,run['job']);self.assertEqual(job['state'],'failed')
        state=manager.snapshot(ws,run['run'])['runs'][0];self.assertEqual(state['result']['summary'],{'passed':1,'failed':1,'error':0,'skipped':0});failure=next(x for x in state['result']['results'] if x['status']=='failed');self.assertEqual(failure['path'],'tests/test_calc.py');self.assertEqual(failure['line'],8)
        self.assertIn('test_bridge.py',state['plan']['commands'][-1][2]);self.assertTrue((state['result']['output']))
        run=manager.start(ws,{'framework':'unittest','selection':'tests/test_calc.py::CalcTests.test_ok','consent':True});self.assertEqual(wait(self.app.features.hilo,run['job'])['state'],'done')
        result=manager.snapshot(ws,run['run'])['runs'][0]['result'];self.assertEqual(len(result['results']),1);self.assertEqual(result['summary']['passed'],1)
    def test_invalid_selection_and_untrusted_run_never_start_a_process(self):
        manager=self.app.features.tests;ws=self.app.workspace
        with self.assertRaises(ValueError):manager.plan(ws,{'framework':'unittest','selection':'../../outside.py::test_bad'})
        with self.assertRaises(PermissionError):manager.start(ws,{'framework':'unittest'})
        ws.trusted=False
        with self.assertRaises(PermissionError):manager.start(ws,{'framework':'unittest','consent':True})
        self.assertFalse(self.app.runner.jobs)

if __name__=='__main__':unittest.main()
