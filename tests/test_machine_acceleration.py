import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
from backend.machine_acceleration import _detect,probe

class AccelerationTests(unittest.TestCase):
    def setUp(self):_detect.cache_clear()
    def test_only_initialized_hardware_is_selected_and_detection_is_cached(self):
        with patch('backend.machine_acceleration.subprocess.run',return_value=SimpleNamespace(stdout=b'Accelerators supported in QEMU binary:\ntcg\nwhpx\n')),patch('backend.machine_acceleration.probe',return_value={'name':'whpx','available':True,'reason':''}) as boot:
            first=_detect('fixture',1,1,'Windows','AMD64',1);second=_detect('fixture',1,1,'Windows','AMD64',1)
            self.assertEqual(first['preferred'],'whpx');self.assertEqual(first,second);boot.assert_called_once_with('fixture','whpx')
    def test_failed_hardware_and_a_different_guest_isa_fall_back_to_tcg(self):
        with patch('backend.machine_acceleration.subprocess.run',return_value=SimpleNamespace(stdout=b'tcg\nhvf\n')),patch('backend.machine_acceleration.probe',return_value={'name':'hvf','available':False,'reason':'not available'}) as boot:
            self.assertEqual(_detect('fixture',1,1,'Darwin','x86_64',1)['preferred'],'tcg');self.assertEqual(_detect('fixture',1,1,'Darwin','arm64',1)['preferred'],'tcg');boot.assert_called_once()
    def test_probe_never_attaches_a_disk_or_runs_a_guest(self):
        process=MagicMock();process.poll.return_value=None
        with patch('backend.machine_acceleration.subprocess.Popen',return_value=process) as run,patch('backend.machine_acceleration.socket.create_connection'),patch('backend.machine_acceleration.qmp_status',return_value={'status':'running','running':True}):
            self.assertTrue(probe('fixture','whpx')['available']);args=run.call_args.args[0];self.assertIn('-S',args);self.assertNotIn('-drive',args);self.assertIn('-nodefaults',args);process.kill.assert_called_once()

    def test_vm_budget_includes_other_running_machines_and_releases_closed_ones(self):
        from backend.machines import Machines
        with tempfile.TemporaryDirectory() as folder:
            disk=Path(folder)/'disk.qcow2';disk.write_bytes(b'fixture');terminal=SimpleNamespace(closed=False)
            machine=Machines.__new__(Machines);machine.profiles=[{'id':'other','memory':3072,'cpus':3}];machine.active={'other':'t1'};machine.root=Path(folder);machine.vm_base=lambda:{'qemu':'fixture'}
            machine.features=SimpleNamespace(terminals=SimpleNamespace(sessions={'t1':terminal}));profile={'id':'new','disk':str(disk),'memory':2048,'cpus':2}
            with patch('backend.machine_acceleration.detect',return_value={'preferred':'tcg'}),patch('psutil.virtual_memory',return_value=SimpleNamespace(available=4*1024**3)),patch('os.cpu_count',return_value=4),patch('shutil.disk_usage',return_value=SimpleNamespace(free=128*1024**2)):
                blocked=machine.readiness(profile);self.assertFalse(blocked['ready']);self.assertEqual(blocked['reservedMemoryMiB'],3072);self.assertEqual(blocked['reservedCpus'],3)
                terminal.closed=True;released=machine.readiness(profile);self.assertTrue(released['ready'],released);self.assertEqual(released['reservedMemoryMiB'],0)

if __name__=='__main__':unittest.main()
