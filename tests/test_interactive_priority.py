import threading,time,unittest
from backend.hilo import Hilo

class InteractionPriorityTests(unittest.TestCase):
 def test_file_action_finishes_while_background_investigation_is_busy(self):
  hilo=Hilo(None);started=threading.Event();release=threading.Event();quick=threading.Event()
  try:
   hilo.submit('Investigation',lambda event:(started.set(),release.wait(3)),workspace='project');self.assertTrue(started.wait(1))
   hilo.submit('Move files',lambda event:quick.set(),workspace='project',priority=-5);self.assertTrue(quick.wait(1));self.assertFalse(release.is_set())
  finally:release.set();hilo.shutdown()
 def test_priority_change_moves_queued_job_without_running_it_twice(self):
  hilo=Hilo(None);started=threading.Event();release=threading.Event();done=threading.Event();runs=[]
  try:
   hilo.submit('Busy',lambda event:(started.set(),release.wait(3)));self.assertTrue(started.wait(1))
   task=hilo.submit('Pending',lambda event:(runs.append(1),done.set()));hilo.prioritize(task['job'],-5);self.assertTrue(done.wait(1));release.set();hilo.queue.join();self.assertEqual(runs,[1])
  finally:release.set();hilo.shutdown()
 def test_interactive_dependent_does_not_bypass_its_background_prerequisite(self):
  hilo=Hilo(None);started=threading.Event();release=threading.Event();done=threading.Event()
  try:
   prior=hilo.submit('Prerequisite',lambda event:(started.set(),release.wait(3)),workspace='one');self.assertTrue(started.wait(1))
   hilo.submit('Dependent',lambda event:done.set(),workspace='one',priority=-10,depends=[prior['job']]);self.assertFalse(done.wait(.2));release.set();self.assertTrue(done.wait(1))
  finally:release.set();hilo.shutdown()

if __name__=='__main__':unittest.main()
