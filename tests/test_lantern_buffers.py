import tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.lantern_adapters import stage,buffer_sources
from backend.runtime_paths import find_tool

ROOT=Path(__file__).resolve().parents[1]

class LanternBuffers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.project=self.base/'Project with spaces';self.project.mkdir()
        self.app=Application(ROOT,self.project,data_dir=self.base/'profile')
        self.ws=self.app.workspace;self.ws.trusted=True;self.live=self.app.features.lantern
    def tearDown(self):
        self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def finished(self,generation):
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            state=self.live.snapshot()
            if state.get('generation')==generation:
                if state.get('executedGeneration')==generation and state.get('code') is not None:return state
                if state.get('error'):return state
            time.sleep(.03)
        self.fail(str(self.live.snapshot()))
    def test_java_uses_unsaved_sibling_and_rebuilds_without_changing_main_or_disk(self):
        if not find_tool('javac') or not find_tool('java'):self.skipTest('JDK unavailable')
        main='public class Main { public static void main(String[] args) { System.out.println(new Calculadora().suma(3,5)); } }'
        helper='public class Calculadora { public double suma(double a,double b) { return a+b; } }'
        (self.project/'Main.java').write_text('saved main is deliberately invalid')
        (self.project/'Calculadora.java').write_text('')
        state=self.app.features.post('/lantern/start',{'path':'Main.java','content':main,'version':7,
             'buffers':[{'path':'Calculadora.java','content':helper}]})
        state=self.finished(state['generation']);self.assertEqual(state.get('code'),0,state['output']);self.assertIn('8.0',state['output'])
        # A dependency edit must trigger even when the main buffer/version is unchanged.
        changed=helper.replace('return a+b','return a+b+1')
        state=self.app.features.post('/lantern/buffer',{'path':'Main.java','content':main,'version':7,
             'buffers':[{'path':'Calculadora.java','content':changed}]})
        second=self.finished(state['generation']);self.assertEqual(second.get('code'),0,second['output']);self.assertIn('9.0',second['output'])
        self.assertGreater(second['revision'],1)
        self.assertEqual((self.project/'Calculadora.java').read_text(),'')
        self.assertEqual((self.project/'Main.java').read_text(),'saved main is deliberately invalid')
        # Closing/reverting an unsaved dependency must remove its previous overlay.
        state=self.live.buffer(self.ws,'Main.java',main,7,[])
        failed=self.finished(state['generation']);self.assertIn('cannot access Calculadora',failed['output'])
        self.assertEqual(failed['status'],'waiting')
        self.assertEqual(len(self.live.history),2)
    def test_python_new_unsaved_dependency_and_evidence_use_same_sources(self):
        main='from helper import VALUE\nprint(VALUE)\n'
        (self.project/'main.py').write_text('print("saved")\n')
        state=self.live.start(self.ws,'main.py',main,1,[{'path':'helper.py','content':'VALUE=42\n'}])
        state=self.finished(state['generation']);self.assertEqual(state.get('code'),0,state['output']);self.assertIn('42',state['output'])
        self.assertFalse((self.project/'helper.py').exists())
        self.assertEqual({row['path'] for row in state['history'][-1]['context']['files']},{'main.py','helper.py'})
        generation=self.live.generation
        self.live.buffer(self.ws,'main.py',main,1,[{'path':'helper.py','content':'VALUE=42\n'}])
        self.assertEqual(self.live.generation,generation)
    def test_invalid_context_does_not_supersede_active_revision(self):
        state=self.live.start(self.ws,'main.py','print(1)\n',1)
        generation=state['generation']
        for rows in ([{'path':'../outside.py','content':'bad'}],[{'path':'.env','content':'secret'}],
                     [{'path':'build/helper.py','content':'bad'}],[{'path':'main.py','content':'bad'}],
                     [{'path':'helper.py','content':'x'*(2*1024*1024+1)}],[{}]*200):
            with self.assertRaises((ValueError,PermissionError)):
                self.live.buffer(self.ws,'main.py','print(2)\n',2,rows)
            self.assertEqual(self.live.generation,generation)
        with self.assertRaisesRegex(ValueError,'4 MiB'):
            buffer_sources(self.ws,'main.py','a'*1024,[{'path':'a.py','content':'a'*(2*1024*1024)},{'path':'b.py','content':'b'*(2*1024*1024)}])
    def test_stage_keeps_saved_dependencies_and_normalizes_overlay_paths(self):
        (self.project/'saved.py').write_text('VALUE=1\n')
        shadow=stage(self.ws,'main.py','print(2)\n',self.base/'shadow',lambda:False,
                     [{'path':'nested\\helper.py','content':'VALUE=2\n'}])
        self.assertEqual(shadow.read('nested/helper.py')['content'],'VALUE=2\n')
        self.assertEqual(shadow.read('saved.py')['content'],'VALUE=1\n')
        self.assertFalse((self.project/'main.py').exists())

if __name__=='__main__':unittest.main()
