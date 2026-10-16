"""Atomic binary patches, source compilation, executable output and conflicts."""
import base64,hashlib,shutil,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.workspace import ConflictError
from backend.binary_view import revision
from backend.binary_tools import java_name
ROOT=Path(__file__).resolve().parents[1]

class BinaryEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();base=Path(self.tmp.name);self.ws=base/'project';self.ws.mkdir();self.app=Application(ROOT,self.ws,data_dir=base/'profile');self.app.workspace.trusted=True;self.tools=self.app.features.binary_tools
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
    def patch(self,path,offset,before,after,stamp=None):
        enc=lambda raw:base64.b64encode(raw).decode();return self.tools.save({'path':path,'revision':stamp or revision(self.ws/path),'patches':[{'offset':offset,'before':enc(before),'after':enc(after)}]})
    def build(self,path,source,success=True):
        result=self.tools.build({'path':path,'source':source,'revision':revision(self.ws/path)});job=self.app.runner.jobs[result['job']];deadline=time.monotonic()+30
        while not job.done and time.monotonic()<deadline:time.sleep(.03)
        self.assertTrue(job.done)
        if success:self.assertEqual(job.code,0,job.output);return self.tools.finish({'job':job.id})
        self.assertNotEqual(job.code,0)
        with self.assertRaisesRegex(ValueError,'falló'):self.tools.finish({'job':job.id})
    def run_binary(self,path,marker):
        result=self.app.features.hacker.start(self.app.workspace,path,'','binary');terminal=self.app.features.terminals.get(result['terminal']['id']);deadline=time.monotonic()+12
        while not terminal.closed and time.monotonic()<deadline:time.sleep(.03)
        self.assertTrue(terminal.closed);self.assertIn(marker,terminal.read()['data'])
    def test_atomic_edit_preserves_bytes_backup_and_detects_external_changes(self):
        file=self.ws/'sample.bin';original=bytes(range(256))*6;file.write_bytes(original)
        result=self.patch('sample.bin',700,original[700:704],b'ABCD');expected=original[:700]+b'ABCD'+original[704:]
        self.assertEqual(file.read_bytes(),expected);self.assertEqual(Path(result['backup']).read_bytes(),original);self.assertEqual(file.stat().st_size,len(original))
        old=result['revision'];file.write_bytes(b'external\x00')
        with self.assertRaises(ConflictError):self.patch('sample.bin',0,b'e',b'z',old)
        self.assertEqual(file.read_bytes(),b'external\x00')
        with self.assertRaises(ConflictError):self.patch('sample.bin',0,b'x',b'z')
        self.assertEqual(file.read_bytes(),b'external\x00')
    def test_invalid_patch_and_untrusted_mutations_leave_original_intact(self):
        file=self.ws/'data.bin';file.write_bytes(b'\0ABC')
        self.app.workspace.trusted=False
        with self.assertRaises(PermissionError):self.patch('data.bin',0,b'\0',b'X')
        self.app.workspace.trusted=True
        with self.assertRaises(ValueError):self.patch('data.bin',0,b'\0',b'XX')
        with self.assertRaises(PermissionError):self.tools.info('../outside')
        self.assertEqual(file.read_bytes(),b'\0ABC')
        self.assertFalse(self.tools.info('data.bin')['canRun'])
    def test_real_c_binary_patch_rebuild_run_and_failed_build_preserves_artifact(self):
        file=self.ws/'hello.exe';file.write_bytes(b'\0placeholder');source=self.ws/'hello.c';source.write_text('#include <stdio.h>\nint main(){puts("ORIGINAL");return 0;}\n')
        self.build('hello.exe','hello.c');self.run_binary('hello.exe','ORIGINAL')
        raw=file.read_bytes();offset=raw.index(b'ORIGINAL\0');self.patch('hello.exe',offset,b'ORIGINAL',b'PATCHED!');self.run_binary('hello.exe','PATCHED!')
        source.write_text('#include <stdio.h>\nint main(){puts("REBUILT");return 0;}\n');self.build('hello.exe','hello.c');self.run_binary('hello.exe','REBUILT')
        before=hashlib.sha256(file.read_bytes()).hexdigest();source.write_text('this is not C;');self.build('hello.exe','hello.c',False);self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),before)
        self.assertEqual(self.tools.info('hello.exe')['source'],'hello.c')
    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'JDK unavailable')
    def test_real_java_class_and_jar_rebuild_then_execute_with_qualified_name(self):
        (self.ws/'pkg').mkdir();file=self.ws/'pkg/Main.class';file.write_bytes(b'\0placeholder');(self.ws/'pkg/Main.java').write_text('package pkg; public class Main {public static void main(String[] a){System.out.println("JAVA_BINARY");}}')
        self.build('pkg/Main.class','pkg/Main.java');self.assertEqual(java_name(file),'pkg/Main');self.run_binary('pkg/Main.class','JAVA_BINARY')
        (self.ws/'program.jar').write_bytes(b'\0placeholder');self.build('program.jar','pkg/Main.java');self.run_binary('program.jar','JAVA_BINARY')

if __name__=='__main__':unittest.main()
