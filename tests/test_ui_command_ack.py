"""UI commands return success only after an actual renderer acknowledgement."""
import threading,unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend.extension_services import ExtensionServices

class UICommandAckTest(unittest.TestCase):
 def setUp(self):
  self.service=object.__new__(ExtensionServices);self.service.lock=threading.RLock();self.service.prompts={};self.host=SimpleNamespace(workspace=SimpleNamespace(trusted=True));self.events=[]
 def test_all_four_commands_wait_for_the_renderer(self):
  for command in ('workbench.action.selectTheme','workbench.action.showCommands','workbench.action.quickOpen','workbench.action.openSettings'):
   def emit(name,**event):
    self.events.append((name,event));self.assertIn(event['request'],self.service.prompts);self.service.answer_prompt(event['request'],{'ok':True})
   self.service.emit=emit;self.assertIsNone(self.service.call(self.host,'command.execute',{'id':command,'args':['main.py']}));self.assertEqual(self.service.prompts,{})
  self.assertEqual(len(self.events),4)
 def test_renderer_failure_and_absence_reject_and_release_request(self):
  self.service.emit=lambda name,**event:self.service.answer_prompt(event['request'],{'ok':False,'error':'No hay temas'})
  with self.assertRaisesRegex(ValueError,'No hay temas'):self.service.call(self.host,'command.execute',{'id':'workbench.action.selectTheme'})
  self.assertFalse(self.service.prompts);self.service.emit=lambda *a,**k:None
  with patch('threading.Event.wait',return_value=False),self.assertRaisesRegex(ValueError,'no confirmó'):self.service.call(self.host,'command.execute',{'id':'workbench.action.quickOpen'})
  self.assertFalse(self.service.prompts)
 def test_unknown_and_untrusted_commands_are_rejected(self):
  with self.assertRaisesRegex(ValueError,'no implementado'):self.service.call(self.host,'command.execute',{'id':'unknown'})
  self.host.workspace.trusted=False
  with self.assertRaises(PermissionError):self.service.call(self.host,'command.execute',{'id':'workbench.action.showCommands'})
