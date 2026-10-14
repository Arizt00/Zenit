"""Actual offline wheel installation and shared interpreter selection."""
import json,os,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
from backend.foundation import bundled_tool,python_command
from backend.lantern_adapters import stage,prepare,runtime_commands
ROOT=Path(__file__).resolve().parents[1]

def wheel(workspace,version='1.0.0'):
    directory=workspace/'.lumen';directory.mkdir(exist_ok=True)
    name=f'zenit_qa_package-{version}-py3-none-any.whl';dist=f'zenit_qa_package-{version}.dist-info'
    files={'zenit_qa_package/__init__.py':f'VALUE = "actual wheel {version}"\n',f'{dist}/METADATA':f'Metadata-Version: 2.1\nName: zenit-qa-package\nVersion: {version}\nSummary: Offline verification wheel\n',f'{dist}/WHEEL':'Wheel-Version: 1.0\nGenerator: Zenit verification\nRoot-Is-Purelib: true\nTag: py3-none-any\n'}
    files[f'{dist}/RECORD']=''.join(f'{path},,\n' for path in [*files,f'{dist}/RECORD'])
    with zipfile.ZipFile(directory/name,'w') as z:
        for path,content in files.items():z.writestr(path,content)
    (workspace/'requirements.txt').write_text('--no-index\n.lumen/'+name+'\n',encoding='utf-8')
    return name

def wait_job(app,result):
    job=app.runner.jobs[result['job']];end=time.monotonic()+60
    while not job.done:
        if time.monotonic()>end:job.cancel();raise AssertionError('Python package task timed out')
        time.sleep(.05)
    if job.code:raise AssertionError(job.output)
    return job

class PythonPackagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.ws=self.root/'project';self.ws.mkdir()
        (self.ws/'main.py').write_text('from zenit_qa_package import VALUE\nprint(VALUE)\n')
        self.app=Application(ROOT,self.ws,data_dir=self.root/'profile');self.manager=self.app.features.python_packages
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
    def test_untrusted_project_cannot_prepare_or_install(self):
        with self.assertRaises(PermissionError):self.manager.start(self.app.workspace,{'action':'create'})
        self.assertFalse((self.ws/'.venv').exists());self.assertFalse(self.manager.status(self.app.workspace)['environment']['ready'])
    def test_invalid_option_url_and_multiline_never_start_a_task(self):
        self.app.workspace.trusted=True
        for value in ['--target ../outside','https://example.com/pkg.whl','requests\n--user','x @ https://example.com/a.whl','a; import os']:
            with self.subTest(requirement=value),self.assertRaises(ValueError):self.manager.start(self.app.workspace,{'action':'install','requirement':value})
        self.assertFalse(self.app.runner.jobs);self.assertFalse((self.ws/'.venv').exists())
    def test_actual_install_run_lantern_debug_and_local_removal(self):
        self.app.workspace.trusted=True;wheel(self.ws)
        wait_job(self.app,self.manager.start(self.app.workspace,{'action':'requirements'}))
        state=self.manager.status(self.app.workspace);self.assertTrue(state['environment']['ready']);self.assertIn({'name':'zenit-qa-package','version':'1.0.0','summary':'Offline verification wheel'},state['packages'])
        self.assertTrue((self.ws/'.venv/pyvenv.cfg').read_text().find('include-system-site-packages = true')>=0)
        plan=self.app.features.runtimes.plan(self.app.workspace,'main.py');self.assertEqual(plan['commands'][0][0],state['environment']['python'])
        self.assertIn('actual wheel 1.0.0',wait_job(self.app,self.app.runner.start(plan['commands'],self.ws)).output)
        forge=self.app.features.hacker.start(self.app.workspace,'main.py',(self.ws/'main.py').read_text(),'python')['terminal']
        terminal=self.app.features.terminals.get(forge['id']);end=time.monotonic()+10
        while 'actual wheel 1.0.0' not in terminal.output and time.monotonic()<end:time.sleep(.05)
        self.assertIn('actual wheel 1.0.0',terminal.output);terminal.close()
        shadow=stage(self.app.workspace,'main.py',(self.ws/'main.py').read_text(),self.root/'shadow',lambda:False)
        live=prepare(self.app.features.runtimes,shadow,'main.py');commands=runtime_commands(live,self.root/'checkpoint.json',self.root/'lens.json')
        self.assertEqual(commands[0][0],state['environment']['python']);self.assertIn('actual wheel 1.0.0',wait_job(self.app,self.app.runner.start(commands,shadow.root)).output)
        debugger=self.app.features.debugger;debugger.start(self.app.workspace,'main.py',[]);end=time.monotonic()+10
        while debugger.snapshot()['status'] in ('running','paused') and time.monotonic()<end:
            if debugger.snapshot()['status']=='paused':debugger.command('continue')
            time.sleep(.05)
        self.assertIn('actual wheel 1.0.0',debugger.snapshot()['output'])
        wait_job(self.app,self.manager.start(self.app.workspace,{'action':'check'}))
        with self.assertRaisesRegex(ValueError,'pip is required'):self.manager.start(self.app.workspace,{'action':'uninstall','requirement':'pip'})
        wait_job(self.app,self.manager.start(self.app.workspace,{'action':'uninstall','requirement':'zenit_qa_package'}))
        self.assertNotIn('zenit-qa-package',[x['name'] for x in self.manager.status(self.app.workspace)['packages']])
        self.assertTrue(Path(self.manager.base()).is_file())
    def test_incomplete_environment_is_preserved(self):
        self.app.workspace.trusted=True;(self.ws/'.venv').mkdir();marker=self.ws/'.venv/mine.txt';marker.write_text('keep')
        with self.assertRaisesRegex(ValueError,'incomplete'):self.manager.start(self.app.workspace,{'action':'create'})
        self.assertEqual(marker.read_text(),'keep')
    def test_partial_python_bundle_preserves_other_shared_sdk_tools(self):
        first=self.root/'base';second=self.root/'shared';first.mkdir();second.mkdir();(first/'python.exe').write_bytes(b'python');(second/'java.exe').write_bytes(b'java')
        for path,tools in [(first,{'python':'python.exe'}),(second,{'java':'java.exe'})]:(path/'tool-index.json').write_text(json.dumps({'schema':1,'tools':tools}))
        with patch('backend.foundation.roots',return_value=[first,second]):self.assertEqual(bundled_tool('java'),str((second/'java.exe').resolve()))

if __name__=='__main__':unittest.main()
