import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.runtime_paths import find_tool
from backend.machines import Machines

class QemuDetectionTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows installer discovery')
 def test_standard_install_is_detected_even_when_running_process_path_is_stale(self):
  with tempfile.TemporaryDirectory() as root:
   folder=Path(root)/'qemu';folder.mkdir()
   for name in ('qemu-system-x86_64','qemu-img','qemu-system-aarch64'):(folder/(name+'.exe')).touch()
   with patch.dict(os.environ,{'ProgramFiles':root}),patch('backend.runtime_paths.shutil.which',return_value=None),patch('backend.foundation.bundled_tool',return_value=None):
    for name in ('qemu-system-x86_64','qemu-img','qemu-system-aarch64'):self.assertEqual(Path(find_tool(name)),folder/(name+'.exe'))
 def test_qemu_is_independent_of_a_foundation_bundle_and_guest_image(self):
  with tempfile.TemporaryDirectory() as root:
   features=SimpleNamespace(prefs=SimpleNamespace(directory=Path(root)),runtimes=SimpleNamespace(config={}))
   machines=Machines(features)
   with patch('backend.machines.inventory',return_value=(None,{})),patch('backend.machines.find_tool',side_effect=lambda n,c=None:n+'.exe'):
    state=machines.vm_base();self.assertEqual(state['qemu'],'qemu-system-x86_64.exe');self.assertEqual(state['qimg'],'qemu-img.exe');self.assertIsNone(state['image'])
    machines.base_root=str(Path(root)/'removed-sdk');self.assertEqual(machines.vm_base()['qemu'],'qemu-system-x86_64.exe')

if __name__=='__main__':unittest.main()
