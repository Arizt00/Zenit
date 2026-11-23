import unittest
from types import SimpleNamespace
from backend.terminals import TerminalSession

class GracefulTerminalCloseTests(unittest.TestCase):
 def test_shutdown_hook_precedes_process_tree_cancellation(self):
  events=[];session=TerminalSession.__new__(TerminalSession);session.id='guest';session.closed=False;session.win=None;session.process=None;session.thread=SimpleNamespace(join=lambda **kw:None);session.governor=SimpleNamespace(cancel_tree=lambda identity:events.append('cancel-tree'))
  session.before_close=lambda:events.append('flush-guest-disk');session.close();self.assertEqual(events,['flush-guest-disk','cancel-tree']);self.assertTrue(session.closed)
 def test_failed_shutdown_hook_does_not_force_a_disk_writer_closed(self):
  events=[];session=TerminalSession.__new__(TerminalSession);session.id='guest';session.closed=False;session.governor=SimpleNamespace(cancel_tree=lambda identity:events.append('cancel-tree'))
  def waiting():raise ValueError('Disk still flushing')
  session.before_close=waiting
  with self.assertRaisesRegex(ValueError,'flushing'):session.close()
  self.assertFalse(events);self.assertFalse(session.closed)

if __name__=='__main__':unittest.main()
