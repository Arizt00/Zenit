"""Real language builds and tests from each scaffold; no user project is modified."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from backend.server import Application
from backend.foundation import tool_environment
from backend.runtime_paths import find_tool
from backend.project_layout import project_info

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(find_tool(name) for name in ('gcc','g++','cmake','ninja','nasm','javac','java','rustc','cargo','ncc')), 'Prepared multi-language SDK required')
class LanguageProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='zenit-language-projects-',ignore_cleanup_errors=True)
        self.root=Path(self.tmp.name);self.project=self.root/'Workspace with spaces';self.project.mkdir()
        self.app=Application(ROOT,self.project,data_dir=self.root/'profile');self.ws=self.app.workspace;self.ws.trusted=True
        self.flow=self.app.features.workflows;self.rt=self.app.features.runtimes

    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()

    def execute(self,commands):
        task=self.app.runner.start(commands,self.project,timeout=90,env=tool_environment())
        job=self.app.runner.jobs[task['job']];deadline=time.monotonic()+100
        while not job.done and time.monotonic()<deadline:time.sleep(.025)
        self.assertTrue(job.done,job.output);self.assertEqual(job.code,0,job.output);return job

    def create(self,language):
        plan=self.flow.scaffold_plan(self.ws,{'language':language,'folder':'project-'+language})
        result=self.flow.scaffold(self.ws,{'plan':plan['id']})
        if result.get('task'):
            job=self.app.runner.jobs[result['task']['job']];deadline=time.monotonic()+30
            while not job.done and time.monotonic()<deadline:time.sleep(.025)
            self.assertEqual(job.code,0,job.output)
            folder=self.project/result['folder'];manifest=json.loads((folder/'ncc.package.json').read_text())
            result['entry']=(folder/manifest['targets']['main']).relative_to(self.project).as_posix()
        return result['entry']

    def test_each_language_has_its_own_real_structure_and_build_folder(self):
        catalog={item['id']:item for item in self.flow.catalog(self.ws)['kits']}
        self.assertEqual(set(catalog),{'c','cpp','asm','java','python','rust','nc'})
        for language in catalog:
            if not catalog[language]['ready']:self.fail('SDK required for this integration test: '+language)
            with self.subTest(language=language):
                entry=self.create(language);file=self.project/entry;source=file.read_bytes()
                plan=self.rt.plan(self.ws,entry)
                job=self.execute(plan['commands']);self.assertEqual(file.read_bytes(),source)
                layout=plan['layout'];self.assertIn('/build/'+language+'/',layout['directory'])
                self.assertTrue((self.project/layout['descriptor']).is_file())
                if language not in ('asm',):self.assertTrue('42' in job.output or language=='nc',job.output)
                self.assertTrue(plan['target'].exists())
                if language in ('c','cpp'):
                    header=self.project/plan['artifacts']['header'];self.assertEqual(header.suffix,'.h' if language=='c' else '.hpp')
                    self.assertIn('include',header.parts)
                    database=self.project/layout['directory']/'compile_commands.json';self.assertTrue(database.is_file())
                if language in ('python','java','rust','nc'):
                    self.assertFalse(list(file.parent.glob('*.h')))
                    self.assertFalse(list(file.parent.glob('*.hpp')))
                if language=='asm':self.assertTrue((file.parents[1]/'include/main.inc').is_file())

    def test_project_tests_really_run_for_c_cpp_python_java_and_rust(self):
        for language in ('c','cpp','python','java','rust'):
            with self.subTest(language=language):
                entry=self.create(language);file=self.project/entry;plan=self.rt.plan(self.ws,entry)
                self.execute(plan['commands']);info=project_info(self.ws,file,language);folder=self.project/plan['layout']['directory']
                if language in ('c','cpp'):
                    self.execute([[find_tool('cmake'),'--build',str(folder),'--parallel','2']])
                    output=self.execute([[find_tool('ctest'),'--test-dir',str(folder),'--output-on-failure']]).output
                    self.assertIn('100% tests passed',output)
                elif language=='python':
                    self.assertIn('OK',self.execute([[sys.executable,'-m','unittest','discover','-s',str(info['root']/'tests')]]).output)
                elif language=='java':
                    classes=folder/'test-classes';classes.mkdir()
                    self.execute([[find_tool('javac'),'-sourcepath',str(info['root']/'src/main/java'),'-d',str(classes),str(file),str(info['root']/'src/test/java/app/MainTest.java')],
                                  [find_tool('java'),'-cp',str(classes),'app.MainTest']])
                else:
                    output=self.execute([[find_tool('cargo'),'test','--manifest-path',str(info['root']/'Cargo.toml'),
                        '--target-dir',str(folder/'cargo-target'),'--tests','--config','build.rustc='+json.dumps(find_tool('rustc')),'--color','never']]).output
                    self.assertIn('1 passed',output)

    def test_python_build_produces_bytecode_without_executing_user_code(self):
        entry=self.create('python');file=self.project/entry;file.write_text('raise RuntimeError("MUST_NOT_RUN")\n')
        plan=self.flow.plan(self.ws,{'path':entry,'action':'build'})
        task=self.flow.run(self.ws,{'plan':plan['id']});job=self.app.runner.jobs[task['job']];deadline=time.monotonic()+20
        while not job.done and time.monotonic()<deadline:time.sleep(.025)
        self.assertEqual(job.code,0,job.output);self.assertTrue(Path(plan['target']).is_file());self.assertEqual(Path(plan['target']).suffix,'.pyc')

    def test_modified_project_header_invalidates_a_reviewed_plan(self):
        entry=self.create('c');plan=self.flow.plan(self.ws,{'path':entry,'action':'run'})
        header=self.project/'project-c/include/app.h';header.write_text(header.read_text()+'\n// new interface revision\n')
        with self.assertRaisesRegex(ValueError,'cambiaron'):self.flow.run(self.ws,{'plan':plan['id']})

    def test_implementation_and_entry_share_one_build_target(self):
        entry=self.create('c');first=self.rt.plan(self.ws,entry)
        implementation='project-c/src/app.c';second=self.rt.plan(self.ws,implementation)
        self.assertEqual(first['target'],second['target'])
        self.assertEqual(first['artifacts']['cmake'],second['artifacts']['cmake'])
        index=json.loads((self.project/'.lumen/native/targets.json').read_text())
        self.assertEqual(len(index),1)
        self.assertIn('42',self.execute(second['commands']).output)

    def test_cmake_preserves_dependency_compile_and_link_arguments(self):
        entry=self.create('c');dependency=self.project/'Library with spaces';dependency.mkdir()
        (dependency/'dep.h').write_text('int dependency_answer(void);\n')
        (dependency/'dep.c').write_text('int dependency_answer(void) { return 42; }\n')
        archive=dependency/'libanswer.a';obj=dependency/'dep.o'
        compiler=find_tool('gcc');ar=Path(compiler).with_name('ar.exe' if os.name=='nt' else 'ar')
        self.execute([[compiler,'-c',str(dependency/'dep.c'),'-o',str(obj)],[str(ar),'rcs',str(archive),str(obj)]])
        source=self.project/'project-c/src/app.c'
        source.write_text('#include "app.h"\n#include "dep.h"\n#ifndef DEPENDENCY_ENABLED\n#error dependency flags lost\n#endif\nint answer(void) { return dependency_answer(); }\n')
        active=self.project/'.lumen/dependencies/active.json';active.parent.mkdir(parents=True,exist_ok=True)
        active.write_text(json.dumps({'compile':['-I'+str(dependency),'-DDEPENDENCY_ENABLED=1'],'link':[str(archive)]}))
        self.rt.config['languages']['c']={'standard':'c99'}
        plan=self.rt.plan(self.ws,entry);self.assertIn('42',self.execute(plan['commands']).output)
        database=json.loads((self.project/plan['layout']['directory']/'compile_commands.json').read_text())
        self.assertTrue(any('-std=gnu99' in row['command'] or '-std=c99' in row['command'] for row in database))
        reviewed=self.flow.plan(self.ws,{'path':entry,'action':'run'})
        active.write_text(json.dumps({'compile':[],'link':[]}))
        with self.assertRaisesRegex(ValueError,'cambiaron'):self.flow.run(self.ws,{'plan':reviewed['id']})

    def test_nested_python_environment_is_selected_without_global_configuration(self):
        entry=self.create('python');root=self.project/'project-python';environment=root/'.venv'
        subprocess.run([sys.executable,'-m','venv','--without-pip',str(environment)],check=True,capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        plan=self.rt.plan(self.ws,entry);expected=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        self.assertEqual(Path(plan['commands'][0][0]),expected);self.assertIn('42',self.execute(plan['commands']).output)


if __name__=='__main__':unittest.main()
