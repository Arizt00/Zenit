"""Real CRDT convergence over TCP, host permissions and bounded execution."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pycrdt import Doc,Text
from backend.server import Application
from backend.team import encode,decode

ROOT=Path(__file__).resolve().parents[1]

class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();base=Path(self.temp.name);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('print("team")\n',encoding='utf-8')
        self.app=Application(ROOT,ws,data_dir=base/'profile');self.app.workspace.trusted=True
        self.service=self.app.features.team
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def start(self,**extra):return self.service.start(self.app.workspace,{'documents':[{'path':'main.py','text':'print("team")\n'}],**extra})
    def peer(self,name,**extra):return self.service.request({'action':'sync','peer':name,'vectors':{},**extra})
    def test_concurrent_unicode_edits_converge_and_save_preserves_external_conflict(self):
        self.start();initial=decode(self.peer('one')['updates']['main.py']);a=Doc({'text':Text()});b=Doc({'text':Text()});a.apply_update(initial);b.apply_update(initial)
        state_a=a.get_state();state_b=b.get_state();a['text'].insert(0,'# Ana 🙂\n');b['text'].insert(0,'# Bea λ\n')
        self.peer('one',updates={'main.py':encode(a.get_update(state_a))});self.peer('two',updates={'main.py':encode(b.get_update(state_b))})
        for doc,name in [(a,'one'),(b,'two')]:doc.apply_update(decode(self.peer(name,vectors={'main.py':encode(doc.get_state())})['updates']['main.py']))
        self.assertEqual(str(a['text']),str(b['text']));self.assertIn('# Ana 🙂',str(a['text']));self.assertIn('# Bea λ',str(a['text']))
        self.assertNotIn('# Ana', (self.app.workspace.root/'main.py').read_text())
        self.service.request({'action':'save','path':'main.py'});self.assertEqual((self.app.workspace.root/'main.py').read_text(encoding='utf-8'),str(a['text']))
        (self.app.workspace.root/'main.py').write_text('external\n')
        with self.assertRaisesRegex(ValueError,'fuera del equipo'):self.service.request({'action':'save','path':'main.py'})
        self.assertEqual((self.app.workspace.root/'main.py').read_text(),'external\n')
    def test_remote_guest_authentication_revocation_and_shared_environment(self):
        status=self.start();url,token=status['invitation'].split('#');body=json.dumps({'peer':'remote','vectors':{}}).encode()
        with self.assertRaises(HTTPError) as error:urlopen(Request(url+'v1',data=body,method='POST'),timeout=2)
        self.assertEqual(error.exception.code,403)
        request=Request(url+'v1',data=body,headers={'Authorization':'Bearer '+token},method='POST')
        with urlopen(request,timeout=2) as response:result=json.load(response)
        self.assertEqual(result['environment']['workspace'],'project');self.assertTrue(result['environment']['shared']);self.assertIn('main.py',result['paths'])
        save=Request(url+'v1',data=json.dumps({'action':'save','path':'main.py'}).encode(),headers={'Authorization':'Bearer '+token},method='POST')
        with self.assertRaises(HTTPError) as error:urlopen(save,timeout=2)
        self.assertEqual(error.exception.code,403)
        self.service.stop();self.assertFalse(self.service.status()['active'])
        with self.assertRaises(OSError):urlopen(request,timeout=1)
    def test_two_zenit_backends_join_and_read_the_same_buffer(self):
        status=self.start();base=Path(self.temp.name);other=base/'other';other.mkdir();guest=Application(ROOT,other,data_dir=base/'guest-profile');guest.workspace.trusted=True
        try:
            guest.features.team.join(guest.workspace,status['invitation']);result=guest.features.team.request({'peer':'other-ide','vectors':{}})
            self.assertEqual(result['room'],status['room']);self.assertIn('main.py',result['updates'])
            with self.assertRaises(PermissionError):self.peer('bad',updates={'../secret':encode(b'\x00\x00')})
        finally:guest.features.shutdown();guest.runner.shutdown()
    def test_yjs_node_peer_uses_real_wire_format(self):
        status=self.start();source="""import * as Y from './web/team-vendor/yjs.mjs';
const [url,key]=process.argv[1].split('#');const sync=body=>fetch(url+'v1',{method:'POST',headers:{Authorization:'Bearer '+key},body:JSON.stringify({peer:'vscode',vectors:{},...body})}).then(r=>r.json());
const initial=await sync({});const doc=new Y.Doc();Y.applyUpdate(doc,Buffer.from(initial.updates['main.py'],'base64'));const before=Y.encodeStateVector(doc);doc.getText('text').insert(0,'# VS Code 🚀\\n');await sync({updates:{'main.py':Buffer.from(Y.encodeStateAsUpdate(doc,before)).toString('base64')}});console.log('YJS_OK');"""
        result=subprocess.run(['node','--input-type=module','-e',source,status['invitation']],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('YJS_OK',result.stdout);self.assertIn('# VS Code 🚀',str(self.service.room.documents['main.py']['text']))
    def test_checkpoint_restores_crdt_without_writing_disk_and_only_owner_restores(self):
        self.start();checkpoint=self.service.request({'action':'checkpoint','label':'Antes'})
        doc=self.service.room.documents['main.py'];doc['text'].insert(0,'# edit\n')
        with self.assertRaises(PermissionError):self.service.room.request({'action':'restore','id':checkpoint['id']})
        self.service.request({'action':'restore','id':checkpoint['id']})
        self.assertEqual(str(doc['text']),'print("team")\n');self.assertEqual((self.app.workspace.root/'main.py').read_text(),'print("team")\n')
        with self.assertRaisesRegex(ValueError,'anfitrión'):self.service.join(self.app.workspace,self.service.url)

    def test_participants_have_no_fixed_product_cap_and_execution_is_explicit(self):
        self.start()
        for index in range(80):self.peer(str(index))
        self.assertEqual(len(self.peer('last')['peers']),81)
        with self.assertRaises(PermissionError):self.service.request({'action':'run','path':'main.py'})
        self.start(allowRun=True);result=self.service.request({'action':'run','path':'main.py'});job=self.app.runner.jobs[result['job']]
        import time
        deadline=time.monotonic()+10
        while not job.done and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(job.done);output=self.service.request({'action':'job','job':job.id});self.assertIn('team',output['output']);self.assertEqual(output['code'],0)
        with self.assertRaises(PermissionError):self.service.request({'action':'job','job':'not-shared'})

if __name__=='__main__':unittest.main()
