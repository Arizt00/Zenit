"""Real interactive children, selected terminals, input ownership and cancellation."""
import json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
from backend.terminals import terminal_profiles
from backend.terminal_execution import start

ROOT=Path(__file__).resolve().parents[1]

class TerminalExecutionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='zenit-terminal-routing-');root=Path(self.tmp.name);self.ws=root/'project';self.ws.mkdir()
  for name in ['one.py','two.py']:(self.ws/name).write_text('# source\n')
  self.app=Application(ROOT,self.ws,data_dir=root/'profile');self.app.workspace.trusted=True;self.f=self.app.features
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def terminal(self,index=0):
  profiles=terminal_profiles();self.assertTrue(profiles)
  info=self.f.terminals.create(self.app.workspace,profiles[min(index,len(profiles)-1)]['id'],True)
  return self.f.terminals.get(info['id'])
 def wait(self,fn):
  deadline=time.monotonic()+15
  while time.monotonic()<deadline:
   value=fn()
   if value:return value
   time.sleep(.03)
  self.fail('No llegó el resultado de la terminal real.')
 def plan(self,source):return {'language':'python','cwd':self.ws,'commands':[[sys.executable,'-u','-c',source]]}
 def test_two_selected_terminals_route_input_and_output_once_and_retain_shells(self):
  one=self.terminal();two=self.terminal(1)
  def plan(ws,path):
   return self.plan('import sys; print("READY_'+path+'",flush=True); value=input(); print("RESULT_'+path+'="+value,flush=True)')
  with patch.object(self.f.runtimes,'plan',side_effect=plan):
   for t,path in [(one,'one.py'),(two,'two.py')]:start(self.f,self.app.workspace,{'id':t.id,'path':path})
  self.wait(lambda:'READY_one.py' in one.output and 'READY_two.py' in two.output)
  self.assertTrue(one.write('FIRST\r'));self.assertTrue(two.write('SECOND\r'))
  self.wait(lambda:not one.execution_channel.state['running'] and not two.execution_channel.state['running'])
  self.assertIn('RESULT_one.py=FIRST',one.output);self.assertNotIn('RESULT_two.py',one.output)
  self.assertIn('RESULT_two.py=SECOND',two.output);self.assertNotIn('RESULT_one.py',two.output)
  self.assertEqual(one.output.count('RESULT_one.py=FIRST'),1);self.assertEqual(len(self.f.terminals.sessions),2)
  self.assertFalse(one.closed);self.assertFalse(two.closed)
  self.assertEqual(one.read()['execution']['code'],0);self.assertEqual(two.read()['execution']['code'],0)
 def test_busy_terminal_rejects_second_run_and_stop_does_not_close_shell(self):
  t=self.terminal()
  with patch.object(self.f.runtimes,'plan',return_value=self.plan('import time; print("WAITING",flush=True); time.sleep(60)')):
   start(self.f,self.app.workspace,{'id':t.id,'path':'one.py'})
   with self.assertRaisesRegex(ValueError,'ya está ejecutando'):start(self.f,self.app.workspace,{'id':t.id,'path':'two.py'})
  self.wait(lambda:'WAITING' in t.output);child=t.execution_channel.child;t.execution_channel.stop()
  self.wait(lambda:not t.execution_channel.state['running']);self.assertTrue(child.closed);self.assertFalse(t.closed)
 def test_compile_failure_never_launches_program_and_all_output_stays_in_selected_terminal(self):
  t=self.terminal();other=self.terminal()
  plan=self.plan('print("BUILD_FAILED"); raise SystemExit(7)');plan['commands'].append([sys.executable,'-c','print("MUST_NOT_RUN")'])
  with patch.object(self.f.runtimes,'plan',return_value=plan):start(self.f,self.app.workspace,{'id':t.id,'path':'one.py'})
  self.wait(lambda:not t.execution_channel.state['running'])
  self.assertEqual(t.read()['execution']['code'],7);self.assertIn('BUILD_FAILED',t.output);self.assertNotIn('MUST_NOT_RUN',t.output);self.assertNotIn('BUILD_FAILED',other.output)
 def test_terminal_from_other_project_is_rejected(self):
  t=self.terminal();t.cwd=str(self.ws.parent)
  with self.assertRaisesRegex(ValueError,'otro proyecto'):start(self.f,self.app.workspace,{'id':t.id,'path':'one.py'})

if __name__=='__main__':unittest.main()
