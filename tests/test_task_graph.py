import threading,time,unittest
from backend.hilo import Hilo
from tests.test_hilo_tern import wait
class TaskGraphTests(unittest.TestCase):
 def test_priority_does_not_deadlock_prerequisites(self):
  hilo=Hilo(None);gate=threading.Event();started=threading.Event();order=[]
  try:
   hilo.submit('gate',lambda e:(started.set(),gate.wait(4)),workspace='one');self.assertTrue(started.wait(2))
   first=hilo.submit('prepare',lambda e:order.append('prepare'),workspace='one',priority=10)
   second=hilo.submit('compile',lambda e:order.append('compile'),workspace='one',priority=-10,depends=[first['job']])
   third=hilo.submit('tests',lambda e:order.append('tests'),workspace='one',priority=-20,depends=[second['job']])
   gate.set();self.assertEqual(wait(hilo,third['job'])['state'],'done');self.assertEqual(order,['prepare','compile','tests'])
   self.assertIsInstance(wait(hilo,first['job'])['workerCpuMs'],(int,float))
  finally:gate.set();hilo.shutdown()
 def test_failure_and_cancellation_propagate_without_executing_dependents(self):
  hilo=Hilo(None);gate=threading.Event();started=threading.Event()
  try:
   def fail(e):started.set();gate.wait(3);raise ValueError('fixture failure')
   first=hilo.submit('prepare',fail,workspace='one');self.assertTrue(started.wait(2))
   second=hilo.submit('compile',lambda e:self.fail('ran after failure'),workspace='one',depends=[first['job']])
   third=hilo.submit('test',lambda e:self.fail('ran after failure'),workspace='one',depends=[second['job']]);gate.set()
   self.assertEqual(wait(hilo,first['job'])['state'],'failed');self.assertEqual(wait(hilo,third['job'])['state'],'cancelled')
   active=threading.Event();root=hilo.submit('cancel',lambda e:(active.set(),e.wait(3)),workspace='one');self.assertTrue(active.wait(2))
   child=hilo.submit('child',lambda e:self.fail('ran after cancellation'),workspace='one',depends=[root['job']]);hilo.cancel(root['job'])
   self.assertEqual(wait(hilo,child['job'])['state'],'cancelled')
  finally:gate.set();hilo.shutdown()
 def test_dependencies_are_bounded_and_workspace_scoped(self):
  hilo=Hilo(None)
  try:
   first=hilo.submit('one',lambda e:None,workspace='one');wait(hilo,first['job'])
   with self.assertRaises(ValueError):hilo.submit('two',lambda e:None,workspace='two',depends=[first['job']])
   with self.assertRaises(ValueError):hilo.submit('missing',lambda e:None,depends=['missing'])
   with self.assertRaises(ValueError):hilo.submit('priority',lambda e:None,priority=-100)
  finally:hilo.shutdown()
 def test_pending_priorities_reorder_actual_ready_queue(self):
  hilo=Hilo(None);gate=threading.Event();started=threading.Event();order=[]
  try:
   hilo.submit('gate',lambda e:(started.set(),gate.wait(3)),workspace='one');self.assertTrue(started.wait(2))
   first=hilo.submit('first',lambda e:order.append('first'),workspace='one',priority=0)
   second=hilo.submit('second',lambda e:order.append('second'),workspace='one',priority=20)
   hilo.prioritize(second['job'],-20);gate.set();wait(hilo,first['job']);self.assertEqual(order,['second','first'])
   with self.assertRaises(ValueError):hilo.prioritize(first['job'],0)
  finally:gate.set();hilo.shutdown()
if __name__=='__main__':unittest.main()
