"""R16 orchestration, durable sessions, destination boundaries and optional SDKs."""
import concurrent.futures,copy,json,os,tempfile,threading,time,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.server import Application
from backend.orchestration import Kernel
from backend.hilo import Hilo
from backend.workbenches import Workbenches
from backend import foundation
from tools.package_sdk import package

ROOT=Path(__file__).resolve().parents[1]
class KernelTests(unittest.TestCase):
 def test_modular_dependencies_reverse_cleanup_and_errors_do_not_skip_services(self):
  kernel=Kernel();calls=[];kernel.register('base',object(),shutdown=lambda:calls.append('base'))
  def fail():calls.append('dependent');raise ValueError('fixture')
  kernel.register('dependent',object(),depends=('base',),shutdown=fail)
  with self.assertRaises(ValueError):kernel.register('broken',object(),depends=('missing',))
  seen=[];remove=kernel.subscribe('shutdown',seen.append);kernel.lifecycle('shutdown');remove()
  self.assertEqual(calls,['dependent','base']);self.assertEqual(len(seen),1);self.assertEqual(kernel.lifecycle_errors[0]['subsystem'],'dependent')
 def test_discovery_is_single_flight_and_invalidation_does_not_publish_old_results(self):
  hilo=Hilo(None);entered=threading.Event();release=threading.Event();calls=[]
  def read():calls.append(1);entered.set();release.wait(3);return {'value':[len(calls)]}
  try:
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(hilo.cached,'fixture',read) for _ in range(4)];self.assertTrue(entered.wait(2));release.set();values=[f.result(3) for f in futures]
   self.assertEqual(len(calls),1);values[0]['value'].append(9);self.assertEqual(hilo.cached('fixture',read),{'value':[1]})
   hilo.invalidate();self.assertEqual(hilo.cached('fixture',read),{'value':[2]})
  finally:hilo.shutdown()
 def test_queue_identity_includes_workspace(self):
  hilo=Hilo(None);release=threading.Event()
  try:
   a=hilo.submit('a',lambda e:release.wait(2),workspace='one',key='same');b=hilo.submit('b',lambda e:True,workspace='two',key='same');self.assertNotEqual(a['job'],b['job'])
  finally:release.set();hilo.shutdown()

class WorkbenchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='zenit-r16-core-');self.base=Path(self.tmp.name);self.ws=self.base/'project';self.ws.mkdir();(self.ws/'main.py').write_text('disk\n');self.app=Application(ROOT,self.ws,data_dir=self.base/'profile');self.app.workspace.trusted=True
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def session(self,text='unsaved ñ'):
  item=self.app.workspace.read('main.py');return {'documents':[{'path':'main.py','dirty':True,'content':text,'revision':item['revision'],'line':2,'column':3,'scrollTop':40}],'active':'main.py','style':'general','layout':{'version':3,'groups':{'left':['project'],'right':['assistant'],'bottom':['console']}},'panes':['main.py']}
 def test_recovery_is_durable_and_never_saves_source(self):
  store=self.app.features.workbenches;source=(self.ws/'main.py').read_bytes();session=self.session();store.checkpoint(self.app.workspace,{'session':session})
  reopened=Workbenches(self.app.features).snapshot(self.app.workspace)['session'];self.assertEqual(reopened['documents'][0]['content'],'unsaved ñ');self.assertEqual(reopened['documents'][0]['scrollTop'],40);self.assertEqual((self.ws/'main.py').read_bytes(),source)
 def test_http_and_disk_recovery_accept_full_text_budget_with_json_escaping(self):
  from backend.server import LumenServer
  from urllib.request import Request,urlopen
  from urllib.error import HTTPError
  server=LumenServer(0,self.app);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
  headers={'Content-Type':'application/json','X-Lumen-Token':self.app.token,'Cookie':f'lumen_session_{server.server_port}='+self.app.token}
  text='\x00'*(2*1024*1024);session={'documents':[{'path':f'draft-{i}.py','dirty':True,'content':text} for i in range(4)]};payload=json.dumps({'session':session}).encode();self.assertGreater(len(payload),48*1024*1024)
  try:
   with urlopen(Request(url+'/api/platform/workbench/session',data=payload,headers=headers),timeout=30) as response:self.assertTrue(json.load(response)['saved'])
   fresh=Workbenches(self.app.features).snapshot(self.app.workspace)['session'];self.assertEqual(len(fresh['documents']),4);self.assertEqual(fresh['documents'][3]['content'],text);self.assertFalse((self.ws/'draft-0.py').exists())
   with urlopen(Request(url+'/api/platform/workbench/spaces/save',data=json.dumps({'name':'Large','session':session}).encode(),headers=headers),timeout=30) as response:self.assertEqual(len(json.load(response)['spaces']),1)
   with self.assertRaises(HTTPError) as caught:urlopen(Request(url+'/api/platform/settings',data=b'{}',headers={**headers,'Content-Length':'3000001'}),timeout=5)
   self.assertEqual(caught.exception.code,400)
  finally:server.shutdown();server.server_close()
 def test_malformed_recovery_is_preserved_before_reset(self):
  store=self.app.features.workbenches;file=store._path(self.app.workspace);file.write_text('[invalid recovery');self.assertIsNone(store.snapshot(self.app.workspace)['session']);backups=list(store.directory.glob('*.corrupt-*.json'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),'[invalid recovery')
 def test_named_spaces_keep_metadata_separate_from_unsaved_recovery(self):
  store=self.app.features.workbenches;store.checkpoint(self.app.workspace,{'session':self.session()});store.save_space(self.app.workspace,{'name':'Coding','session':self.session()});state=store.snapshot(self.app.workspace)
  self.assertNotIn('content',state['spaces'][0]['session']['documents'][0]);self.assertEqual(state['session']['documents'][0]['content'],'unsaved ñ')
  store.save_space(self.app.workspace,{'name':'coding','session':self.session()});self.assertEqual(len(store.snapshot(self.app.workspace)['spaces']),1)
  store.discard(self.app.workspace,'main.py');self.assertEqual(store.snapshot(self.app.workspace)['session']['documents'],[])
 def test_session_bounds_and_workspace_paths_are_enforced(self):
  store=self.app.features.workbenches
  for docs in [[{'path':'../escape.py','dirty':False}],[{'path':'main.py','dirty':True,'content':'x'*(2*1024*1024+1)}],[{'path':'main.py','dirty':False}]*49]:
   with self.assertRaises((ValueError,PermissionError)):store.checkpoint(self.app.workspace,{'session':{'documents':docs}})
 def test_hub_newer_edits_survive_parent_checkpoint_and_project_scopes(self):
  store=self.app.features.workbenches;self.app.features.buffers.update(self.app.workspace,{'path':'main.py','text':'from child','saved':False});store.checkpoint(self.app.workspace,{'session':self.session(),'shared':['main.py']});self.assertEqual(store.snapshot(self.app.workspace)['session']['documents'][0]['content'],'from child')
  other=self.base/'other';other.mkdir();from backend.workspace import Workspace
  self.assertIsNone(store.snapshot(Workspace(other,self.app.native))['session'])
 def test_targets_are_shared_durable_and_remote_argv_is_quoted(self):
  execution=self.app.features.execution
  fake={'id':'wsl:Fixture','label':'WSL · Fixture','kind':'wsl','distribution':'Fixture','executable':'wsl.exe','available':True,'system':'linux'}
  with patch.object(execution,'_wsl',return_value=[fake]):
   self.app.features.hilo.invalidate();execution.select(self.app.workspace,{'id':fake['id']});self.assertEqual(Workbenches(self.app.features).snapshot(self.app.workspace)['target'],fake['id'])
   plan=self.app.features.runtimes.plan(self.app.workspace,'main.py');self.assertEqual(plan['commands'][0][:4],['wsl.exe','--distribution','Fixture','--exec']);self.assertIn('python3 -u',plan['commands'][0][-1]);self.assertNotIn('.exe',plan['commands'][0][-1])
   with self.assertRaisesRegex(ValueError,'Este equipo'):execution.require_local(self.app.workspace,'Checkpoints')
   execution.select(self.app.workspace,{'id':'local'});self.assertEqual(execution.selected(self.app.workspace)['kind'],'local')
 def test_ssh_selection_requires_remote_root_and_never_falls_back(self):
  f=self.app.features;f.machines.profiles=[{'id':'station','mode':'ssh','name':'Station','host':'example.test','port':22,'user':'coder','type':'arch'}]
  with patch('backend.execution_targets.find_tool',return_value='ssh'):
   with self.assertRaises(ValueError):f.execution.select(self.app.workspace,{'id':'ssh:station'})
   f.execution.select(self.app.workspace,{'id':'ssh:station','directory':"/home/coder/project's folder"});plan=f.runtimes.plan(self.app.workspace,'main.py');self.assertEqual(plan['commands'][0][0],'ssh');self.assertIn('example.test',plan['commands'][0]);self.assertIn('python3 -u',plan['commands'][0][-1])
   f.machines.profiles=[]
   with self.assertRaisesRegex(ValueError,'no está disponible'):f.runtimes.plan(self.app.workspace,'main.py')
 def test_real_lantern_checkpoint_reads_are_cached_and_invalidated_on_replace(self):
  lantern=self.app.features.lantern;file=self.base/'state.json';file.write_text('{"value":1}')
  from backend.lantern import read_checkpoint
  with patch('backend.lantern.read_checkpoint',wraps=read_checkpoint) as read:
   self.assertEqual(lantern.read_json(file,100)['value'],1);changed=lantern.read_json(file,100);changed['value']=9;self.assertEqual(lantern.read_json(file,100)['value'],1);self.assertEqual(read.call_count,1)
   with self.assertRaises(ValueError):lantern.read_json(file,2)
   replacement=self.base/'next.json';replacement.write_text('{"value":2}');os.replace(replacement,file);self.assertEqual(lantern.read_json(file,100)['value'],2);self.assertEqual(read.call_count,2)
 def test_sdk_package_is_verified_activated_and_does_not_modify_original(self):
  source=self.base/'sdk';(source/'nasm').mkdir(parents=True);(source/'nasm/nasm.exe').write_bytes(b'fixture-tool');(source/'tool-index.json').write_text(json.dumps({'schema':1,'platform':__import__('sys').platform,'tools':{'nasm':'nasm/nasm.exe'},'components':[{'id':'nasm','version':'fixture'}]}));archive=self.base/'nasm.zip';package(source,'nasm',archive)
  old=list(foundation._additional_roots)
  try:
   result=self.app.features.sdk.install(str(archive));selected=result['roots'][0];self.assertTrue(selected['managed']);self.assertEqual(Path(foundation.bundled_tool('nasm')).read_bytes(),b'fixture-tool');self.assertEqual((source/'nasm/nasm.exe').read_bytes(),b'fixture-tool')
   installed=Path(foundation.bundled_tool('nasm'));installed.write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'cambió'):self.app.features.sdk.install(str(archive))
   corrupt=self.base/'corrupt.zip'
   with zipfile.ZipFile(archive) as z,zipfile.ZipFile(corrupt,'w') as out:
    for name in z.namelist():out.writestr(name,b'corrupt' if name=='nasm/nasm.exe' else z.read(name))
   # An archive with corrupted payload must fail in a fresh managed location.
   with tempfile.TemporaryDirectory() as fresh:
    self.app.features.sdk.directory=Path(fresh)
    with self.assertRaisesRegex(ValueError,'SHA-256'):self.app.features.sdk.install(str(corrupt))
  finally:foundation.set_sdk_roots(old)

if __name__=='__main__':unittest.main()
