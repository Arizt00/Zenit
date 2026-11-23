import hashlib,json,os,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.preferences import Preferences,atomic_json
from backend.downloads import Downloads
from backend.updates import Updates,update_asset
from backend.update_handoff import apply_update
from backend.server import Application
from backend.version import RELEASE_TAG,REPOSITORY

ROOT=Path(__file__).resolve().parents[1]
class ReleaseUpdateTests(unittest.TestCase):
 def asset(self,version):
  return {'tag_name':version,'prerelease':'preview' in version,'body':'Release notes <script>','assets':[{'name':'Zenit-0.6.0-Windows-Setup.exe','digest':'sha256:'+'a'*64,'size':100,'browser_download_url':f'https://github.com/{REPOSITORY}/releases/download/{version}/Zenit-0.6.0-Windows-Setup.exe'}]}
 def test_channel_notes_and_persisted_ready_download(self):
  stable=self.asset('v0.6.0');preview=self.asset('v0.7.0-preview.1')
  self.assertEqual(update_asset([stable,preview],RELEASE_TAG,'win32','AMD64',channel='stable')['version'],'v0.6.0')
  chosen=update_asset([stable,preview],RELEASE_TAG,'win32','AMD64');self.assertEqual(chosen['version'],'v0.7.0-preview.1');self.assertIn('<script>',chosen['notes'])
  with tempfile.TemporaryDirectory() as tmp:
   prefs=Preferences(Path(tmp));downloads=Downloads(tmp);updater=Updates(prefs,downloads)
   with patch('backend.updates.sys.platform','win32'),patch('backend.updates.platform.machine',return_value='AMD64'):
    updater.data.update(available=chosen,download='fixture');updater.persist();downloads.items['fixture']={'id':'fixture','status':'complete','path':str(downloads.root/chosen['name'])}
    restored=Updates(prefs,downloads);self.assertEqual(restored.snapshot()['status'],'ready');self.assertEqual(restored.snapshot()['available']['version'],chosen['version'])
   self.assertTrue(updater.welcome()['show']);updater.welcome(ack=True);self.assertFalse(Updates(prefs,downloads).welcome()['show']);downloads.shutdown()
 def test_install_waits_preserves_profile_restarts_only_after_exit(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);profile=base/'profile';target=base/'installed';target.mkdir();(target/'installation.json').write_text('{}');(target/'Zenit.exe').write_bytes(b'old launcher');atomic_json(profile/'settings.json',{'theme':'forest'});source=base/'project';source.mkdir();(source/'main.c').write_text('user project')
   installer=base/'verified.exe';installer.write_bytes(b'fixture installer');request=profile/'updates/handoff-fixture.json';data={'profile':str(profile),'target':str(target),'workspace':str(source),'pid':123,'processCreated':1,'created':time.time(),'version':'v0.6.0','installer':str(installer),'sha256':hashlib.sha256(installer.read_bytes()).hexdigest()};atomic_json(request,data)
   order=[]
   class Installer:
    def __init__(self,target):self.target=target
    def _install(self,options):order.append('install');self.options=options
    def status(self):return {'status':'finished'}
   apply_update(request,Installer,wait=lambda data:order.append('exit'),launch=lambda exe,ws:order.append('launch'))
   self.assertEqual(order,['exit','install','launch']);self.assertEqual(json.loads((profile/'settings.json').read_text()),{'theme':'forest'});self.assertEqual((source/'main.c').read_text(),'user project');self.assertTrue(list((profile/'updates/backups').glob('*.zip')))
   with self.assertRaises(TimeoutError):apply_update(request,Installer,wait=lambda data:(_ for _ in ()).throw(TimeoutError('editor active')),launch=lambda *a:order.append('duplicate'))
   self.assertNotIn('duplicate',order)

 def test_preflight_failure_leaves_editor_running_without_relaunch(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);profile=base/'profile';target=base/'installed';target.mkdir();(target/'installation.json').write_text('{}');(target/'Zenit.exe').write_bytes(b'old launcher');request=profile/'updates/handoff-preflight.json';atomic_json(request,{'profile':str(profile),'target':str(target),'workspace':str(base),'pid':123,'processCreated':1,'created':time.time(),'version':'v0.6.0'})
   order=[]
   class Installer:
    def __init__(self,target):pass
    def preflight(self):raise ValueError('ruta demasiado larga')
   with self.assertRaisesRegex(ValueError,'ruta demasiado larga'):apply_update(request,Installer,wait=lambda data:order.append('wait'),launch=lambda *a:order.append('launch'))
   self.assertEqual(order,[]);self.assertEqual(json.loads((profile/'updates/install-result.json').read_text())['state'],'error');self.assertEqual((target/'Zenit.exe').read_bytes(),b'old launcher')

 @unittest.skipUnless(os.name=='nt','Windows path-budget preflight')
 def test_installer_rejects_long_destination_before_copying(self):
  from installer import Installer
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);payload=base/'payload';payload.mkdir();(payload/'zenit.exe').write_bytes(b'fixture');target=base/('destination-'+'x'*120)/('nested-'+'x'*60)
   with self.assertRaisesRegex(ValueError,'demasiado larga'):Installer(payload=payload,target=target).preflight()
   self.assertFalse(target.exists())

 @unittest.skipUnless(os.name=='nt','Windows rollback path-budget preflight')
 def test_reinstall_path_budget_includes_the_previous_payload(self):
  from installer import Installer
  from backend.version import VERSION,REVISION
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);payload=base/'payload';payload.mkdir();(payload/'zenit.exe').write_bytes(b'fixture');(payload/('p'*90)).write_bytes(b'data');target=base/('t'*(145-len(str(base))-1));(target/f'app-{VERSION}-R{REVISION}').mkdir(parents=True)
   self.assertLess(len(str(target))+19+90,260)
   with self.assertRaisesRegex(ValueError,'demasiado larga'):Installer(payload=payload,target=target).preflight()

class MachineLibraryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.app.workspace.trusted=True;self.library=self.app.features.machine_images;self.ws=self.app.workspace;self.event=threading.Event();self.qimg=self.app.features.machines.vm_base().get('qimg')
  if not self.qimg:self.tearDown();self.skipTest('QEMU SDK unavailable')
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def run_qimg(self,*args):return subprocess.check_output([self.qimg,*args],timeout=30,creationflags=0x08000000 if os.name=='nt' else 0)
 def image(self):
  source=self.base/'source.qcow2';self.run_qimg('create','-f','qcow2',str(source),'4M');digest=hashlib.sha256(source.read_bytes()).hexdigest();image=self.library.import_image(self.ws,{'path':str(source),'sha256':digest,'system':'linux'},self.event)['image'];return source,image
 def test_operations_deduplicate_only_identical_requests(self):
  with patch.object(self.library,'import_image',side_effect=lambda ws,body,event:event.wait(.5)):
   first=self.app.features.post('/machines/images/import',{'name':'first'});same=self.app.features.post('/machines/images/import',{'name':'first'});other=self.app.features.post('/machines/images/import',{'name':'second'})
   self.assertEqual(first['job'],same['job']);self.assertNotEqual(first['job'],other['job'])
 def test_real_sparse_clone_export_restore_and_volatile_cleanup(self):
  source,image=self.image();original=source.read_bytes();created=self.library.create(self.ws,{'image':image['id'],'memory':1024},self.event)['machine'];disk=Path(created['disk']);self.assertLess(disk.stat().st_size,2_000_000)
  self.library.save(self.ws,{'id':created['id'],'file':'saved.tern'});self.library.close_workspace(self.ws);self.assertTrue(disk.is_file());restored=self.library.reopen(self.ws,{'file':'saved.tern'})['machine'];self.assertEqual(restored['id'],created['id'])
  result=self.library.export(self.ws,{'id':created['id'],'file':'portable.qcow2'},self.event);info=json.loads(self.run_qimg('info','--output=json',str(self.project/result['file'])));self.assertNotIn('backing-filename',info);self.assertEqual(source.read_bytes(),original)
  volatile=self.library.create(self.ws,{'image':image['id'],'memory':1024},self.event)['machine'];self.library.discard(self.ws,volatile['id']);self.assertFalse(Path(volatile['disk']).exists());self.assertTrue(disk.exists())
 def test_wrong_digest_and_backing_file_rejected(self):
  source,image=self.image()
  with self.assertRaisesRegex(ValueError,'SHA-256'):self.library.import_image(self.ws,{'path':str(source),'sha256':'0'*64},self.event)
  overlay=self.base/'overlay.qcow2';self.run_qimg('create','-f','qcow2','-F','qcow2','-b',str(source),str(overlay),'4M')
  with self.assertRaisesRegex(ValueError,'independiente'):self.library.import_image(self.ws,{'path':str(overlay),'sha256':hashlib.sha256(overlay.read_bytes()).hexdigest()},self.event)
  self.assertEqual(len(self.library.images),1)
 def test_imported_disk_boots_real_qemu_and_reuses_one_guest(self):
  from backend.runtime_paths import find_tool
  nasm=find_tool('nasm')
  if not nasm:self.skipTest('NASM required for the real boot-sector fixture')
  source=self.base/'boot.asm';raw=self.base/'boot.bin';image=self.base/'boot.qcow2'
  source.write_text('bits 16\norg 0x7c00\nmov dx, 0x3f8\n'+''.join('mov al, '+str(ord(c))+'\nout dx, al\n' for c in 'ZENIT055BOOT\r\n')+'again: hlt\njmp again\ntimes 510-($-$$) db 0\ndw 0xaa55\n')
  subprocess.run([nasm,'-f','bin',str(source),'-o',str(raw)],check=True,capture_output=True,timeout=15,creationflags=0x08000000 if os.name=='nt' else 0);self.run_qimg('convert','-f','raw','-O','qcow2',str(raw),str(image))
  imported=self.library.import_image(self.ws,{'path':str(image),'sha256':hashlib.sha256(image.read_bytes()).hexdigest()},self.event)['image'];created=self.library.create(self.ws,{'image':imported['id'],'memory':1024},self.event)['machine'];first=self.library.start(self.ws,created['id']);second=self.library.start(self.ws,created['id']);self.assertEqual(first['id'],second['id'])
  terminal=self.app.features.terminals.sessions[first['id']];deadline=time.monotonic()+40
  while 'ZENIT055BOOT' not in terminal.output and time.monotonic()<deadline and not terminal.closed:time.sleep(.1)
  self.assertIn('ZENIT055BOOT',terminal.output);self.library.stop(self.ws,created['id']);self.assertTrue(terminal.closed)

if __name__=='__main__':unittest.main()
