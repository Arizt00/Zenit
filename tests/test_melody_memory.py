import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.melody_memory import MelodyMemory
from backend.preferences import Preferences
from backend.providers import AIRouter

class MelodyMemoryTest(unittest.TestCase):
    def test_persistent_bounded_scoped_memory_and_forget_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);memory=MelodyMemory(directory);key=memory.key(tmp,'main.py','codex')
            for i in range(9):memory.remember(key,0,'main.py','request '+str(i),'answer '*3000,'hash')
            restored=MelodyMemory(directory);messages,entry,epoch=restored.messages(key)
            self.assertLessEqual(len(messages),12);self.assertIn('request 8',str(messages));self.assertNotIn('request 0',str(messages))
            self.assertFalse(restored.messages(restored.key(tmp,'other.py','codex'))[0]);self.assertFalse(restored.messages(restored.key(tmp,'main.py','ollama'))[0])
            restored.forget(key);restored.remember(key,epoch,'main.py','stale response','answer','hash');self.assertFalse(restored.read(key)[0]['turns'])
    def test_followup_new_conversation_receives_memory_and_current_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefs=Preferences(Path(tmp));router=AIRouter(prefs);captured=[]
            def stream(job,messages,system,timeout):captured.append((messages,system));job.append('A specific explanation of the previous code.')
            def request(question,content,conversation):
                result=router.start({'provider':'codex','model':'test-model','question':question,'content':content,'path':'main.py','conversation':conversation,'consent':True,'memory':True,'memoryWorkspace':tmp})
                job=router.get(result['id']);end=time.time()+5
                while not job.done and time.time()<end:time.sleep(.01)
                self.assertFalse(job.error);self.assertTrue(job.done)
            with patch.object(router,'_authorize'),patch.object(router.accounts,'stream',side_effect=stream):
                request('Explain this','value = 1','first');router.clear_history();request('Now change it','value = 2','second')
            messages,system=captured[-1];self.assertIn('Explain this',str(messages));self.assertIn('previous code',str(messages));self.assertIn('value = 2',messages[-1]['content']);self.assertNotIn('value = 1',str(messages));self.assertIn('Source changed since the remembered turn: True',system)
            router.shutdown()
