import json,os,shutil,subprocess,tempfile,threading,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
from tests.test_hilo_tern import wait
from tests.test_python_packages import wheel

ROOT=Path(__file__).resolve().parents[1]

class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.app.workspace.trusted=True
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def test_offline_bundle_reconstructs_real_packages_in_another_project(self):
        ws=self.app.workspace;t=self.app.features.tern;p=t.portability;event=threading.Event()
        task=self.app.features.post('/lantern/environments/create',{'kind':'python','name':'Portable fixture','inherit':False});job=wait(self.app.features.hilo,task['job'],90);self.assertEqual(job['state'],'done',job)
        identity=job['result']['environment'];directory=t.directory(ws,identity);name=wheel(self.project)
        p.run(ws,[str(t.python(directory)),'-I','-m','pip','--isolated','install','--no-index',str(self.project/'.lumen'/name)],event,'Fixture package installation')
        t.save(ws,identity,'portable.tern');data=json.loads((self.project/'portable.tern').read_text());self.assertEqual(data['schema'],2);self.assertIn({'name':'zenit-qa-package','version':'1.0.0','editable':False},data['dependencies'])
        missing=p.export(ws,{'file':'portable.tern'},event);self.assertFalse(missing['report']['complete']);self.assertTrue(missing['report']['missing']);(self.project/missing['file']).unlink()
        resources=p.resource_folder(directory,'wheels');shutil.copy2(self.project/'.lumen'/name,resources/name)
        seed=Path(subprocess.check_output([self.app.features.python_packages.base(),'-I','-c','import ensurepip,pathlib;print(pathlib.Path(ensurepip.__file__).parent / "_bundled")'],text=True,creationflags=0x08000000 if os.name=='nt' else 0).strip())
        for item in seed.glob('*.whl'):shutil.copy2(item,resources/item.name)
        bundle=p.export(ws,{'file':'portable.tern'},event);self.assertTrue(bundle['report']['complete'],bundle)
        with self.assertRaises(FileExistsError):p.export(ws,{'file':'portable.tern'},event)
        other=self.base/'other';other.mkdir();shutil.copy2(self.project/bundle['file'],other/bundle['file']);second=Application(ROOT,other,data_dir=self.base/'other-profile');second.workspace.trusted=True
        try:
            target=second.features.tern;checked=target.portability.inspect(second.workspace,bundle['file']);self.assertTrue(checked['report']['complete'],checked)
            result=target.portability.rebuild(second.workspace,{'file':bundle['file'],'bundleSha256':checked['report']['bundleSha256'],'consent':True},event);self.assertTrue(result['offline']);self.assertNotEqual(result['environment'],identity)
            python=target.python(target.directory(second.workspace,result['environment']))
            output=subprocess.check_output([str(python),'-I','-c','import zenit_qa_package;print(zenit_qa_package.VALUE)'],text=True,creationflags=0x08000000 if os.name=='nt' else 0)
            self.assertIn('actual wheel 1.0.0',output);self.assertTrue((directory/'environment').is_dir());self.assertTrue((other/result['file']).is_file())
            self.assertEqual(result['receipt']['environmentId'],bundle['report']['environmentId']);self.assertIn('pip-check',result['receipt']['verified'])
            receipt=target.directory(second.workspace,result['environment'])/'reconstruction.json';self.assertEqual(json.loads(receipt.read_text())['bundleSha256'],checked['report']['bundleSha256'])
            with (other/bundle['file']).open('ab') as changed:changed.write(b'CHANGED_AFTER_REVIEW')
            existing=set(target.sessions)
            with self.assertRaisesRegex(ValueError,'cambió desde la revisión'):target.portability.rebuild(second.workspace,{'file':bundle['file'],'bundleSha256':checked['report']['bundleSha256'],'consent':True},event)
            self.assertEqual(set(target.sessions),existing)
        finally:second.features.shutdown();second.runner.shutdown()

    def test_bundle_rejects_unknown_steps_traversal_and_tampered_resources(self):
        ws=self.app.workspace;p=self.app.features.tern.portability
        data={'schema':2,'type':'zenit-environment','id':'a'*32,'kind':'python','name':'fixture','dependencies':[],'tools':[{'name':'python','version':'3.12.0','implementation':'CPython'}],'preparation':[{'action':'python.venv'},{'action':'python.install-locked'}],'artifacts':[]}
        bad={**data,'preparation':[{'action':'shell','command':'untrusted'}]}
        with self.assertRaises(ValueError):p.validate(bad)
        for name,entries in [('traversal',{'../outside':b'x'}),('undeclared',{'unlisted.whl':b'x'}),('tampered',{'wheels/fixture-1.0-py3-none-any.whl':b'x'})]:
            current=dict(data)
            if name=='tampered':current['artifacts']=[{'path':'wheels/fixture-1.0-py3-none-any.whl','bytes':1,'sha256':'0'*64}]
            path=self.project/(name+'.tern.zip')
            with zipfile.ZipFile(path,'w') as bundle:
                bundle.writestr('environment.tern',json.dumps(current));bundle.writestr('report.json','{}')
                for entry,value in entries.items():bundle.writestr(entry,value)
            with self.assertRaises(ValueError):p.inspect(ws,path.name)
        self.assertFalse((self.base/'outside').exists());self.assertFalse(self.app.runner.jobs)

    def test_qcow_export_restores_an_independent_disk_in_another_project(self):
        t=self.app.features.tern;p=t.portability;ws=self.app.workspace;event=threading.Event();base=self.app.features.machines.vm_base()
        if not base.get('qimg') or not base.get('qemu'):self.skipTest('QEMU unavailable')
        image=self.base/'tiny-base.qcow2';subprocess.run([base['qimg'],'create','-f','qcow2',str(image),'4M'],check=True,capture_output=True,timeout=15,creationflags=0x08000000 if os.name=='nt' else 0)
        with patch.object(self.app.features.machines,'vm_base',return_value={**base,'image':str(image)}):
            identity=t.create(ws,{'kind':'arch','name':'Portable disk fixture'},event)['environment'];t.save(ws,identity,'machine.tern');result=p.export(ws,{'file':'machine.tern'},event);self.assertTrue(result['report']['complete'],result)
        other=self.base/'other-vm-project';other.mkdir();shutil.copy2(self.project/result['file'],other/result['file']);second=Application(ROOT,other,data_dir=self.base/'vm-profile');second.workspace.trusted=True
        try:
            restored=second.features.tern.portability.rebuild(second.workspace,{'file':result['file'],'bundleSha256':result['report']['bundleSha256'],'consent':True},event);disk=second.features.tern.directory(second.workspace,restored['environment'])/'disk.qcow2';info=json.loads(subprocess.check_output([base['qimg'],'info','--output=json',str(disk)],timeout=15,creationflags=0x08000000 if os.name=='nt' else 0));self.assertNotIn('backing-filename',info);self.assertEqual(info['format'],'qcow2');self.assertTrue(disk.with_name('seed.iso').is_file());self.assertNotEqual(identity,restored['environment'])

        finally:second.features.shutdown();second.runner.shutdown()

    def fixture_bundle(self,name='fixture.tern.zip',incompatible=False,missing_dependency=False):
        import hashlib,platform
        p=self.app.features.tern.portability;actual=p.inventory(self.app.features.python_packages.base());filename=wheel(self.project);source=self.project/'.lumen'/filename
        if missing_dependency:
            with zipfile.ZipFile(source) as archive:entries={i:archive.read(i) for i in archive.namelist()}
            metadata=next(i for i in entries if i.endswith('/METADATA'));entries[metadata]+=b'Requires-Dist: zenit-qa-deliberately-absent>=1\n'
            with zipfile.ZipFile(source,'w') as archive:
                for key,value in entries.items():archive.writestr(key,value)
        payload=source.read_bytes();filename=filename.replace('py3-none-any','cp27-cp27m-manylinux1_i686') if incompatible else filename
        data={'schema':2,'type':'zenit-environment','kind':'python','name':'Offline check','target':{'kind':'local'},'platform':{'system':platform.system(),'machine':platform.machine()},'dependencies':[{'name':'zenit-qa-package','version':'1.0.0'}],'tools':[{'name':'python','version':actual['version'],'implementation':actual['implementation']}],'preparation':[{'action':'python.venv'},{'action':'python.install-locked'}],'artifacts':[{'path':'wheels/'+filename,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]}
        with zipfile.ZipFile(self.project/name,'w') as archive:archive.writestr('environment.tern',json.dumps(data));archive.writestr('wheels/'+filename,payload)
        return p.inspect(self.app.workspace,name)

    def test_incompatible_wheel_is_reported_before_any_preparation(self):
        report=self.fixture_bundle(incompatible=True)['report'];self.assertFalse(report['complete']);self.assertTrue(any('incompatible' in m for m in report['missing']));self.assertFalse(self.app.runner.jobs)

    def test_inspection_is_cancellable_and_runs_through_the_maintenance_queue(self):
        from concurrent.futures import CancelledError
        checked=self.fixture_bundle();event=threading.Event();event.set()
        with self.assertRaises(CancelledError):self.app.features.tern.portability.inspect(self.app.workspace,'fixture.tern.zip',event=event)
        task=self.app.features.post('/lantern/environments/inspect',{'file':'fixture.tern.zip'});job=wait(self.app.features.hilo,task['job'],60)
        self.assertEqual(job['state'],'done',job);self.assertEqual(job['result']['report']['bundleSha256'],checked['report']['bundleSha256']);self.assertFalse(self.app.features.tern.sessions)

    def test_failed_dependency_check_removes_only_the_new_environment(self):
        result=self.fixture_bundle(missing_dependency=True);self.assertTrue(result['report']['complete'],result)
        t=self.app.features.tern;sentinel=self.project/'keep.txt';sentinel.write_text('existing project')
        with self.assertRaisesRegex(ValueError,'Comprobar dependencias reconstruidas falló'):t.portability.rebuild(self.app.workspace,{'file':'fixture.tern.zip','bundleSha256':result['report']['bundleSha256'],'consent':True},threading.Event())
        self.assertFalse(t.sessions);self.assertEqual(sentinel.read_text(),'existing project');self.assertFalse(list(self.project.glob('.lumen/tern/*/environment')))

    def test_export_refuses_stale_inventory_without_creating_a_bundle(self):
        t=self.app.features.tern;p=t.portability;data=self.fixture_bundle()['descriptor'];data['id']='a'*32
        (self.project/'stale.tern').write_text(json.dumps(data))
        with patch.object(t,'owned',return_value=(self.project,{})),patch.object(p,'inventory',return_value={'version':data['tools'][0]['version'],'implementation':data['tools'][0]['implementation'],'dependencies':[]}):
            with self.assertRaisesRegex(ValueError,'entorno cambió'):p.export(self.app.workspace,{'file':'stale.tern'},threading.Event())
        self.assertFalse((self.project/'stale.tern.zip').exists())
if __name__=='__main__':unittest.main()
