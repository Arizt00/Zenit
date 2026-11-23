"""Real NASM ELF/PE images, CPU simulation, OS boundaries and host execution."""
import os
from pathlib import Path
import tempfile,time,unittest
from backend.simulation import Simulation
from backend.nasm import EXAMPLES,target_system
from backend.workspace import Workspace
from backend.preferences import Preferences
from backend.runtimes import Runtimes
from backend.runner import Runner
from backend.buffers import Buffers

class NasmTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix="zenit-nasm-test-");self.root=Path(self.temp.name);self.ws=Workspace(self.root,None);self.ws.trusted=True;self.sim=Simulation(None)
 def tearDown(self):self.temp.cleanup()
 def run_source(self,source,system="linux",arch="x86_64",steps=100):
  return self.sim.run(self.ws,{"engine":"nasm","system":system,"architecture":arch,"source":source,"steps":steps})
 def test_real_elf32_elf64_and_pe32_pe64_run_without_changing_sources(self):
  for system,examples in EXAMPLES.items():
   for arch,source in examples.items():
    with self.subTest(system=system,arch=arch):
     file=self.root/"original.asm";file.write_text(source);original=file.read_bytes()
     r=self.run_source(source,system,arch)
     self.assertEqual(r["status"],"complete",r);self.assertEqual(r["exitCode"],8,r)
     self.assertEqual(r["format"],("win" if system=="windows" else "elf")+("64" if arch=="x86_64" else "32"));self.assertEqual(file.read_bytes(),original)
 def test_linux_stdout_data_relocations_and_bounded_steps(self):
  source='global _start\nsection .data\nmsg: db "NASM_REAL",10\nlen equ $-msg\nsection .text\n_start:\nmov rax,1\nmov rdi,1\nlea rsi,[rel msg]\nmov rdx,len\nsyscall\nmov rax,60\nxor rdi,rdi\nsyscall\n'
  r=self.run_source(source);self.assertEqual(r["status"],"complete",r);self.assertEqual(r["output"],"NASM_REAL\n");self.assertEqual(r["exitCode"],0)
  r=self.run_source('global _start\nsection .text\n_start:\ninc rbx\njmp _start\n',steps=3);self.assertEqual(r["status"],"paused",r);self.assertEqual(r["executed"],3)
 def test_relative_include_and_explicit_failure_for_unimplemented_services(self):
  (self.root/"value.inc").write_text('%define VALUE 9\n')
  source='%include "value.inc"\nglobal _start\nsection .text\n_start:\nmov rdi,VALUE\nmov rax,60\nsyscall\n'
  self.assertEqual(self.run_source(source)["exitCode"],9)
  r=self.run_source('global _start\nsection .text\n_start:\nmov rax,9999\nsyscall\n');self.assertEqual(r["status"],"fault");self.assertIn("no implementado",r["error"])
  r=self.run_source(EXAMPLES['linux']['x86_64'],system='windows');self.assertEqual(r['status'],'fault');self.assertIn('Windows',r['error'])
 def test_windows_data_relocations_and_unresolved_dll_calls_are_explicit(self):
  r=self.run_source('global main\nsection .data\nnumber: dd 23\nsection .text\nmain:\nmov eax,[rel number]\nret\n',system="windows");self.assertEqual(r["exitCode"],23,r)
  r=self.run_source('global main\nextern ExitProcess\nsection .text\nmain:\ncall ExitProcess\n',system="windows");self.assertEqual(r["status"],"error");self.assertIn("WinAPI",r["error"])
 def test_wrong_system_architecture_bits_and_untrusted_input_are_rejected(self):
  for system,arch in [("unknown","x86_64"),("linux","riscv64")]:
   with self.assertRaises(ValueError):self.run_source("",system,arch)
  r=self.run_source("bits 32\nmov eax,3\n");self.assertEqual(r["status"],"error");self.assertIn("BITS",r["error"])
  self.ws.trusted=False
  with self.assertRaises(PermissionError):self.run_source("")
 def test_native_host_run_and_cross_os_diagnostic_check(self):
  rt=Runtimes(Preferences(self.root/"profile"));file=self.root/"main.asm";host="windows" if os.name=="nt" else "linux";other="linux" if host=="windows" else "windows"
  file.write_text(EXAMPLES[other]["x86_64"])
  with self.assertRaisesRegex(ValueError,"destino"):rt.plan(self.ws,file.name)
  self.assertEqual(len(rt.plan(self.ws,file.name,check=True)["commands"]),1)
  file.write_text(EXAMPLES[host]["x86_64"]);plan=rt.plan(self.ws,file.name);runner=Runner()
  try:
   result=runner.start(plan["commands"],self.root);job=runner.jobs[result["job"]];end=time.monotonic()+20
   while not job.done and time.monotonic()<end:time.sleep(.02)
   self.assertTrue(job.done);self.assertEqual(job.code,8,job.output)
  finally:runner.shutdown()
 def test_syntax_errors_keep_nasm_filename_and_line(self):
  r=self.run_source('global _start\nsection .text\n_start:\nthis_is_not_an_instruction eax,1\n');self.assertEqual(r['status'],'error');self.assertIn('buffer.asm:4',r['error'])
 @unittest.skipUnless(os.name=='nt','Native Windows API requires Windows')
 def test_windows_explicit_entry_calls_real_exitprocess_without_crt(self):
  file=self.root/'entry.asm';file.write_text('; Sistema: Windows\nglobal _start\nextern ExitProcess\nsection .text\n_start:\nsub rsp,40\nmov ecx,8\ncall ExitProcess\n')
  plan=Runtimes(Preferences(self.root/'profile')).plan(self.ws,file.name);runner=Runner()
  try:
   job=runner.jobs[runner.start(plan['commands'],self.root)['job']];end=time.monotonic()+20
   while not job.done and time.monotonic()<end:time.sleep(.02)
   self.assertTrue(job.done);self.assertEqual(job.code,8,job.output)
  finally:runner.shutdown()
 def test_llvm_engine_keeps_its_original_syntax(self):
  r=self.sim.run(self.ws,{'engine':'llvm','architecture':'x86_64','source':'.intel_syntax noprefix\n.text\nmov rax,12\n','steps':10});self.assertEqual(r['status'],'complete',r);self.assertEqual(r['registers']['rax'],'0xc')
 def test_detached_buffer_hydration_preserves_disk_revision_and_unsaved_text(self):
  from backend.native import NativeCore
  self.ws.native=NativeCore(Path(__file__).resolve().parents[1])
  hub=Buffers();file=self.root/'draft.asm';file.write_text('disk\n');hub.update(self.ws,{'path':file.name,'text':'unsaved\n','saved':False})
  data=hub.document(self.ws,file.name);self.assertEqual(data['file']['content'],'disk\n');self.assertEqual(data['buffer']['text'],'unsaved\n');self.assertTrue(data['file']['revision'])
  file.unlink();data=hub.document(self.ws,file.name);self.assertTrue(data['file']['transient']);self.assertIsNone(data['file']['revision']);self.assertEqual(data['file']['content'],'unsaved\n');self.assertFalse(file.exists())
  with self.assertRaises(FileNotFoundError):hub.document(self.ws,'unknown.asm')
  with self.assertRaises(PermissionError):hub.document(self.ws,'../escape.asm')
  with self.assertRaises(PermissionError):hub.document(self.ws,str(self.root.parent/'unknown.asm'))
 def test_native_detach_can_open_a_known_diskless_buffer_but_not_an_unknown_path(self):
  from unittest.mock import MagicMock,patch
  from types import SimpleNamespace
  from backend.desktop import DesktopAPI
  hub=Buffers();hub.update(self.ws,{'path':'draft.asm','text':'mov eax,8','saved':False});api=DesktopAPI();api._url='http://127.0.0.1:1';api._window=MagicMock();api._application=SimpleNamespace(workspace=self.ws,features=SimpleNamespace(buffers=hub))
  with patch('webview.create_window') as create:
   self.assertTrue(api.detach_panel('profile-assembly','draft.asm')['opened']);self.assertIn('file=draft.asm',create.call_args.args[1])
   with self.assertRaises(FileNotFoundError):api.detach_panel('profile-assembly','unknown.asm')

if __name__=="__main__":unittest.main()
