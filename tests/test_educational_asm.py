"""Real educational engine output, bounded execution and native routing."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from backend.simulation import Simulation
from backend.educational_asm import RARS_EXAMPLE,MARS_EXAMPLE,bounded_run
from backend.runtime_paths import find_tool
from backend.workspace import Workspace

class EducationalAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.ws=Workspace(Path(self.temp.name),None);self.ws.trusted=True;self.sim=Simulation(None)
    def tearDown(self):self.temp.cleanup()
    def test_rars_and_mars_run_real_educational_syscalls(self):
        if not find_tool('java'):self.skipTest('Java required')
        for engine,arch,source,register in [('rars','riscv32',RARS_EXAMPLE,'a0'),('rars','riscv64',RARS_EXAMPLE,'a0'),('mars','mips',MARS_EXAMPLE,'$a0')]:
            with self.subTest(engine=engine,architecture=arch):
                result=self.sim.run(self.ws,{'engine':engine,'architecture':arch,'source':source,'steps':10000})
                self.assertEqual(result['status'],'complete',result);self.assertIn('7 + 5 = 12',result['output']);self.assertEqual(int(result['registers'][register],16),12);self.assertIsNone(result['pc'])
    def test_rars_step_limit_input_and_workspace_include(self):
        if not find_tool('java'):self.skipTest('Java required')
        (self.ws.root/'constants.inc').write_text('.eqv ANSWER 17\n')
        result=self.sim.run(self.ws,{'engine':'rars','architecture':'riscv32','source':'.include "constants.inc"\n.text\nli a0, ANSWER\nloop: j loop\n','steps':3,'path':'main.asm'})
        self.assertEqual(result['status'],'paused');self.assertEqual(result['executed'],3);self.assertEqual(int(result['registers']['a0'],16),17)
        result=self.sim.run(self.ws,{'engine':'rars','architecture':'riscv32','source':'.text\nli a7, 5\necall\nli a7, 1\necall\nli a7, 10\necall\n','stdin':'42\n','steps':100})
        self.assertEqual(result['output'],'42')
    def test_wrong_architecture_and_unknown_engine_are_rejected(self):
        for engine,arch in [('rars','arm'),('mars','riscv64'),('invented','x86_64')]:
            with self.assertRaises(ValueError):self.sim.run(self.ws,{'engine':engine,'architecture':arch,'source':'.text\n'})
    def test_simulator_output_budget_terminates_the_process(self):
        with self.assertRaisesRegex(ValueError,'2 MB'):
            bounded_run([sys.executable,'-c','import sys;sys.stdout.write("x"*3000000)'],'',self.ws.root)
    def test_native_runner_rejects_educational_code_and_executes_host_assembly(self):
        from backend.preferences import Preferences
        from backend.runtimes import Runtimes
        from backend.runner import Runner
        runtime=Runtimes(Preferences(self.ws.root/'profile'))
        file=self.ws.root/'program.asm';file.write_text(RARS_EXAMPLE)
        with self.assertRaisesRegex(ValueError,'RARS'):runtime.plan(self.ws,'program.asm')
        if sys.platform!='win32' or not find_tool('nasm') or not find_tool('gcc'):self.skipTest('Windows x64 NASM/GCC fixture')
        file.write_text('global main\nsection .text\nmain:\nmov eax, 42\nret\n')
        plan=runtime.plan(self.ws,'program.asm');runner=Runner()
        try:
            result=runner.start(plan['commands'],self.ws.root);job=runner.jobs[result['job']]
            import time
            deadline=time.monotonic()+15
            while not job.done and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(job.done);self.assertEqual(job.code,42,job.output)
        finally:runner.shutdown()

if __name__=='__main__':unittest.main()
