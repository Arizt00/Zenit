"""Resource bounds and real interactive consoles, including simultaneous runs."""
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.runner import Runner,Job
from backend.server import Application
from backend.lsp import LanguageServers
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

class ExecutionR15(unittest.TestCase):
    def test_shutdown_closes_inflight_language_server_and_rejects_late_starts(self):
        entered=threading.Event();release=threading.Event();closed=[]
        class Session:
            id='server';capabilities={}
            def __init__(self,*args):entered.set();release.wait(3)
            def close(self):closed.append(self.id)
        manager=LanguageServers(SimpleNamespace(audit=lambda *args,**kw:None),SimpleNamespace(config={'servers':[{'id':'test','languages':['python']}]}))
        workspace=SimpleNamespace(trusted=True,root=ROOT)
        with patch('backend.lsp.LanguageSession',Session):
            start=threading.Thread(target=manager.start,args=(workspace,'test',True));start.start();self.assertTrue(entered.wait(2))
            stop=threading.Thread(target=manager.shutdown,kwargs={'permanent':True});stop.start();release.set();start.join(3);stop.join(3)
            self.assertFalse(start.is_alive() or stop.is_alive());self.assertEqual(closed,['server']);self.assertEqual(manager.sessions,{})
            with self.assertRaisesRegex(ValueError,'cerrando'):manager.start(workspace,'test',True)

    def test_foreground_queue_bounds_and_cancelled_work_never_starts(self):
        gate=threading.Event();started=threading.Event();executed=[]
        def run(job):
            if not job.cancelled:
                executed.append(job.id);started.set();gate.wait(5)
            job.done=True
        with patch('backend.runner.os.cpu_count',return_value=2),patch.object(Job,'run',run),tempfile.TemporaryDirectory() as temp:
            runner=Runner()
            try:
                first=runner.start([],Path(temp));self.assertTrue(started.wait(2))
                pending=[runner.start([],Path(temp)) for _ in range(16)]
                self.assertEqual(runner.snapshot()['running'],1);self.assertEqual(runner.snapshot()['queued'],16)
                with self.assertRaisesRegex(ValueError,'llena'):runner.start([],Path(temp))
                for entry in pending:runner.jobs[entry['job']].cancel()
                gate.set()
            finally:gate.set();runner.shutdown()
            self.assertEqual(executed,[first['job']])

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'Java SDK unavailable')
    def test_java_system_console_and_two_independent_interactive_processes(self):
        with tempfile.TemporaryDirectory(prefix='zenit-execution-') as temp:
            base=Path(temp);ws=base/'project';ws.mkdir()
            (ws/'Console.java').write_text('public class Console {public static void main(String[] args) {var c=System.console();if(c==null)throw new IllegalStateException("NO_CONSOLE");System.out.println("CONSOLE_READY");String s=c.readLine();System.out.println("JAVA:"+s);}}',encoding='utf-8')
            (ws/'other.py').write_text('print("PYTHON_READY",flush=True)\nprint("PYTHON:"+input())\n',encoding='utf-8')
            app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
            try:
                result=app.features.hacker.start(app.workspace,'Console.java','','file');job=app.runner.jobs[result['job']]
                deadline=time.monotonic()+25
                while not job.done and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(job.code,0,job.output)
                a=app.features.terminals.get(app.features.hacker.attach(app.workspace,job.id)['id'])
                b=app.features.terminals.get(app.features.hacker.start(app.workspace,'other.py','','file')['terminal']['id'])
                while ('CONSOLE_READY' not in a.read()['data'] or 'PYTHON_READY' not in b.read()['data']) and time.monotonic()<deadline:time.sleep(.03)
                self.assertFalse(a.closed);self.assertFalse(b.closed);self.assertIn('CONSOLE_READY',a.read()['data']);self.assertIn('PYTHON_READY',b.read()['data'])
                a.write('uno\r');b.write('dos\r')
                while (not a.closed or not b.closed) and time.monotonic()<deadline:time.sleep(.03)
                self.assertIn('JAVA:uno',a.read()['data']);self.assertNotIn('PYTHON:dos',a.read()['data'])
                self.assertIn('PYTHON:dos',b.read()['data']);self.assertNotIn('JAVA:uno',b.read()['data'])
                self.assertTrue(a.closed and b.closed)
            finally:app.features.shutdown();app.runner.shutdown()

if __name__=='__main__':unittest.main()
