import subprocess,tempfile,unittest
from pathlib import Path
from backend.binary_structure import inspect,compare
from backend.runtime_paths import find_tool
from backend.terminals import child_environment

class BinaryStructureTests(unittest.TestCase):
 def test_real_pe_elf_symbols_and_paged_version_difference(self):
  gcc=find_tool('gcc');clang=find_tool('clang')
  if not gcc or not clang:self.skipTest('Native SDK unavailable')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'main.c';source.write_text('int exported_value=42; int main(void){return exported_value;}\n');pe=root/'program.exe';elf=root/'program.o'
   subprocess.run([gcc,'-g',str(source),'-o',str(pe)],check=True,capture_output=True,env=child_environment(),timeout=30);subprocess.run([clang,'--target=x86_64-unknown-linux-gnu','-g','-c',str(source),'-o',str(elf)],check=True,capture_output=True,env=child_environment(),timeout=30)
   for file,kind in [(pe,'PE32+'),(elf,'ELF64')]:
    data=inspect(file,file.name);self.assertEqual(data['format'],kind);self.assertEqual(data['architecture'],'x86-64');self.assertTrue(any(s['name']=='.text' for s in data['sections']));self.assertTrue(any(s['name']=='exported_value' for s in data['symbols']),data['symbols'][:20])
   raw=pe.read_bytes();other=root/'version.exe';other.write_bytes(raw[:500]+bytes([raw[500]^1])+raw[501:]+b'extra');first=compare(pe,other,0,512);self.assertEqual(first['differentBytes'],1);self.assertEqual(first['ranges'],[{'offset':500,'count':1}]);self.assertEqual(first['nextOffset'],512);tail=compare(pe,other,len(raw));self.assertEqual(tail['differentBytes'],5);self.assertIsNone(tail['nextOffset']);self.assertTrue(compare(pe,pe)['identicalInRange'])
 def test_malformed_tables_are_bounded_and_do_not_follow_embedded_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/'bad';file.write_bytes(b'MZ'+b'\0'*58+b'\xff'*4)
   with self.assertRaises(ValueError):inspect(file,'bad')
   file.write_bytes(b'\x7fELF'+b'\xff'*100)
   with self.assertRaises(ValueError):inspect(file,'bad')
if __name__=='__main__':unittest.main()
