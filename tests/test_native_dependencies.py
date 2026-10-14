import json,os,subprocess,tempfile,time,unittest
from pathlib import Path
from backend.server import Application
from backend.foundation import bundled_tool,tool_environment
from backend.lantern_adapters import stage,prepare
from backend.native_packages import native_state
from backend.lsp import LanguageSession
ROOT=Path(__file__).resolve().parents[1]

def wait(app,result):
    job=app.runner.jobs[result['job']];end=time.monotonic()+100
    while not job.done:
        if time.monotonic()>end:job.cancel();raise AssertionError('Task timeout: '+job.output)
        time.sleep(.05)
    if job.code:raise AssertionError(job.output)
    return job.output

class NativeDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.ws=self.root/'project';self.ws.mkdir()
        self.app=Application(ROOT,self.ws,data_dir=self.root/'profile');self.manager=self.app.features.native_packages
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
    def test_trust_and_reference_validation(self):
        with self.assertRaises(PermissionError):self.manager.start(self.app.workspace,{'action':'install','requirement':'zlib/1.3.1'})
        self.app.workspace.trusted=True
        for value in ['--profile=x','zlib;echo x','https://x/a','../x/1','zlib/1\n--remote=x']:
            with self.assertRaises(ValueError):self.manager.start(self.app.workspace,{'action':'install','requirement':value})
        self.assertFalse(self.app.runner.jobs)
    @unittest.skipUnless(bundled_tool('python') and bundled_tool('gcc'),'Prepared native base required')
    def test_actual_offline_conan_package_feeds_c_cpp_and_lantern(self):
        self.app.workspace.trusted=True;ws=self.app.workspace
        wait(self.app,self.manager.start(ws,{'action':'resolve','language':'c'}))
        recipe=self.root/'recipe';recipe.mkdir()
        (recipe/'conanfile.py').write_text('from conan import ConanFile\nfrom conan.tools.files import save\nimport os\nclass Package(ConanFile):\n    name="zenit-qa"\n    version="1.0"\n    package_type="header-library"\n    def package(self):\n        save(self, os.path.join(self.package_folder,"include","zenit_qa.h"),"#define ZENIT_VALUE 73\\n")\n',encoding='utf-8')
        env={**os.environ,**tool_environment(),'CONAN_HOME':str(self.ws/'.lumen/dependencies/cache')}
        result=subprocess.run([bundled_tool('python'),'-I','-c','from conans.conan import run; run()','export',str(recipe)],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        subprocess.run([bundled_tool('python'),'-I','-c','from conans.conan import run; run()','remote','disable','*'],env=env,capture_output=True,check=True)
        wait(self.app,self.manager.start(ws,{'action':'install','language':'c','requirement':'zenit-qa/1.0'}))
        self.assertIn('zenit-qa/1.0',native_state(ws)['requires'])
        for name,source in [('main.c','#include <stdio.h>\n#include <zenit_qa.h>\nint main(void){printf("%d",ZENIT_VALUE);return 0;}'),('main.cpp','#include <iostream>\n#include <zenit_qa.h>\nint main(){std::cout<<ZENIT_VALUE;}')]:
            (self.ws/name).write_text(source);plan=self.app.features.runtimes.plan(ws,name)
            self.assertIn('73',wait(self.app,self.app.runner.start(plan['commands'],self.ws)))
            shadow=stage(ws,name,source,self.ws/'.lumen/qa-shadow',lambda:False);self.assertEqual(native_state(shadow)['compile'],native_state(ws)['compile'])
        if bundled_tool('clangd'):
            session=LanguageSession({'argv':[bundled_tool('clangd')],'languages':['c','cpp']},ws)
            try:
                file=self.ws/'main.c';source=file.read_text();uri=file.as_uri()
                session.notify('textDocument/didOpen',{'textDocument':{'uri':uri,'languageId':'c','version':1,'text':source}})
                result=session.request('textDocument/hover',{'textDocument':{'uri':uri},'position':{'line':2,'character':35}},timeout=20)
                self.assertIn('73',json.dumps(result))
                database=json.loads((self.ws/'.lumen/dependencies/lsp/compile_commands.json').read_text())
                self.assertIn('-std=c11',database[0]['arguments']);self.assertIn('-std=c++17',database[1]['arguments'])
            finally:session.close()
        original=native_state(ws)
        bad=self.manager.start(ws,{'action':'install','requirement':'nonexistent-zenit-qa/0.0.0'})
        job=self.app.runner.jobs[bad['job']]
        while not job.done:time.sleep(.1)
        self.assertNotEqual(job.code,0);self.assertEqual(native_state(ws),original)
        wait(self.app,self.manager.start(ws,{'action':'remove','requirement':'zenit-qa/1.0'}));self.assertFalse(native_state(ws)['compile'])
    @unittest.skipUnless(bundled_tool('ncc'),'Prepared nC base required')
    def test_nc_native_manifest_add_and_lock(self):
        self.app.workspace.trusted=True;ws=self.app.workspace
        wait(self.app,self.manager.start(ws,{'language':'nc','action':'init'}))
        wait(self.app,self.manager.start(ws,{'language':'nc','action':'install','requirement':'stoud::io'}))
        self.assertTrue((self.ws/'ncc.lock').is_file());self.assertIn('stoud::io',json.dumps(self.manager.status(ws)['nc']))
        plan=self.app.features.runtimes.plan(ws,'src/main.n',check=True)
        self.assertIn('package',plan['commands'][0]);self.assertIn('check',plan['commands'][0]);wait(self.app,self.app.runner.start(plan['commands'],self.ws))
        before=(self.ws/'src/main.n').read_bytes()
        with self.assertRaises(ValueError):self.manager.start(ws,{'language':'nc','action':'init'})
        self.assertEqual(before,(self.ws/'src/main.n').read_bytes())
    @unittest.skipUnless(os.name=='nt' and bundled_tool('nasm'),'Prepared Windows NASM base required')
    def test_actual_nasm_and_gnu_assembly(self):
        self.app.workspace.trusted=True
        for name,source in [('main.asm','global main\nsection .text\nmain:\n xor eax,eax\n ret\n'),('main.s','.text\n.globl main\nmain:\n xorl %eax,%eax\n ret\n')]:
            (self.ws/name).write_text(source);plan=self.app.features.runtimes.plan(self.app.workspace,name)
            wait(self.app,self.app.runner.start(plan['commands'],self.ws))
