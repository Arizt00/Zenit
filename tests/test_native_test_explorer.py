import os,subprocess,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.runtime_paths import find_tool
from backend.terminals import child_environment
from tests.test_hilo_tern import wait
ROOT=Path(__file__).resolve().parents[1]
class NativeTestExplorerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.ws=self.base/'project';self.ws.mkdir();self.app=Application(ROOT,self.ws,data_dir=self.base/'profile');self.app.workspace.trusted=True
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def test_actual_ctest_preparation_and_junit_results(self):
  cmake=find_tool('cmake')
  if not cmake or not find_tool('ctest'):self.skipTest('CMake/CTest unavailable')
  (self.ws/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(Tests NONE)\nenable_testing()\nadd_test(NAME actual_pass COMMAND "'+str(find_tool('python')).replace('\\','/')+'" -c "raise SystemExit(0)")\nadd_test(NAME actual_fail COMMAND "'+str(find_tool('python')).replace('\\','/')+'" -c "raise SystemExit(1)")\n')
  subprocess.run([cmake,'-S',str(self.ws),'-B',str(self.ws/'build'),'-G','Ninja'],check=True,capture_output=True,env=child_environment(),timeout=20)
  run=self.app.features.tests.start(self.app.workspace,{'framework':'ctest','build':True,'consent':True});self.assertEqual(wait(self.app.features.hilo,run['job'],60)['state'],'failed');state=self.app.features.tests.snapshot(self.app.workspace,run['run'])['runs'][0];self.assertEqual(state['result']['summary']['passed'],1);self.assertEqual(state['result']['summary']['failed'],1);self.assertEqual(len(state['jobs']),2);self.assertEqual(state['result']['code'],8)
 def test_actual_offline_cargo_tests_use_dependency_preparation(self):
  cargo=find_tool('cargo');rustc=find_tool('rustc')
  if not cargo or not rustc:self.skipTest('Cargo/Rust unavailable')
  (self.ws/'src').mkdir();(self.ws/'src/lib.rs').write_text('#[cfg(test)] mod tests { #[test] fn actual_pass(){assert_eq!(2+2,4);} #[test] fn actual_fail(){assert_eq!(2+2,5);} }')
  (self.ws/'Cargo.toml').write_text('[package]\nname="zenit_qa"\nversion="0.1.0"\nedition="2021"\n');(self.ws/'.cargo').mkdir();(self.ws/'.cargo/config.toml').write_text('[net]\noffline=true\n[target.x86_64-pc-windows-gnu]\nlinker="'+str(find_tool('gcc')).replace('\\','/')+'"\n')
  # Select an already-installed toolchain directly; never invoke a rustup download.
  gnu=Path.home()/'.rustup/toolchains/stable-x86_64-pc-windows-gnu/bin/cargo.exe'
  if os.name=='nt' and gnu.is_file():self.app.features.runtimes.config['tools']['cargo']=str(gnu)
  run=self.app.features.tests.start(self.app.workspace,{'framework':'cargo','consent':True});state_job=wait(self.app.features.hilo,run['job'],90);state=self.app.features.tests.snapshot(self.app.workspace,run['run'])['runs'][0];self.assertEqual(state_job['state'],'failed',state);self.assertIsNotNone(state['result'],state);self.assertEqual(state['result']['summary']['passed'],1,state);self.assertEqual(state['result']['summary']['failed'],1,state);self.assertEqual(len(state['jobs']),2)
if __name__=='__main__':unittest.main()
