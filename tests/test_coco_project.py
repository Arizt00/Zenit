from concurrent.futures import ThreadPoolExecutor
import json,tempfile,time,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pycrdt import Doc,Text
from backend.server import Application
from backend.team import encode,decode
ROOT=Path(__file__).resolve().parents[1]

class CoCoProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'host';self.project.mkdir();(self.project/'src').mkdir();(self.project/'main.py').write_text('import time\nwith open("starts.txt","a") as f:f.write("START\\n")\nprint("ONE_HOST",flush=True)\ntime.sleep(.5)\n');(self.project/'src/library.py').write_text('VALUE=42\n');(self.project/'.env').write_text('PRIVATE_FIXTURE=not_shared\n');self.host=Application(ROOT,self.project,data_dir=self.base/'profile');self.host.workspace.trusted=True;self.team=self.host.features.team;self.state=self.team.start(self.host.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]});self.guests=[]
        for index in range(2):
            folder=self.base/('guest'+str(index));folder.mkdir();guest=Application(ROOT,folder,data_dir=self.base/('profile'+str(index)));guest.workspace.trusted=True;guest.features.team.join(guest.workspace,self.state['invitation']);self.guests.append(guest)
    def tearDown(self):
        for guest in self.guests:guest.features.shutdown();guest.runner.shutdown()
        self.host.features.shutdown();self.host.runner.shutdown();self.temp.cleanup()
    def sync(self,index,**data):return self.guests[index].features.team.request({'action':'sync','vectors':{},**data})
    def role(self,index,role):
        peer=self.sync(index)['self']['id'];self.team.request({'action':'permissions','participant':peer,'role':role});return peer
    def test_project_tree_permissions_and_identity_cannot_be_spoofed(self):
        first=self.sync(0);self.assertEqual(first['self']['role'],'viewer');self.assertEqual({x['path'] for x in first['project']['files']},{'main.py','src/library.py'})
        with self.assertRaises(ValueError):self.guests[0].features.team.request({'action':'project-create','path':'blocked.py'})
        peer=self.role(0,'editor');self.guests[0].features.team.request({'action':'project-open','path':'src/library.py'});state=self.sync(0);doc=Doc({'text':Text()});doc.apply_update(decode(state['updates']['src/library.py']));before=doc.get_state();doc['text'].insert(0,'# participant edit\n');update=encode(doc.get_update(before))
        denied=self.sync(1,peer=peer,updates={'src/library.py':update});self.assertFalse(denied['acceptedUpdates']);self.assertNotIn('participant edit',str(self.team.room.documents['src/library.py']['text']))
        self.sync(0,updates={'src/library.py':update});self.assertIn('participant edit',str(self.team.room.documents['src/library.py']['text']))
        url,token=self.state['invitation'].split('#');request=Request(url+'v1',data=json.dumps({'action':'sync','peer':peer,'resumeKey':'incorrect','vectors':{}}).encode(),headers={'Authorization':'Bearer '+token},method='POST')
        with self.assertRaises(HTTPError):urlopen(request,timeout=3)
        identity=dict(self.guests[0].features.team.remote_identity);self.guests[0].features.team.request({'action':'sync','vectors':{}});self.assertEqual(identity,self.guests[0].features.team.remote_identity);self.assertEqual(self.sync(0)['self']['id'],peer)
    def test_rename_preserves_crdt_identity_and_offline_updates_after_old_name_reuse(self):
        self.role(0,'editor');state=self.sync(0);doc=Doc({'text':Text()});doc.apply_update(decode(state['updates']['main.py']));identity=next(x['id'] for x in state['documents'] if x['path']=='main.py');before=doc.get_state();doc['text'].insert(0,'# offline edit\n')
        self.guests[0].features.team.request({'action':'project-rename','path':'main.py','newPath':'src/renamed.py'});self.guests[0].features.team.request({'action':'project-create','path':'main.py','text':'print("NEW_FILE")\n'})
        self.sync(0,documentIds={'main.py':identity},vectors={'main.py':encode(doc.get_state())},updates={'main.py':encode(doc.get_update(before))})
        self.assertIn('offline edit',str(self.team.room.documents['src/renamed.py']['text']));self.assertNotIn('offline edit',str(self.team.room.documents['main.py']['text']));self.assertEqual(self.team.room.project.document_ids['src/renamed.py'],identity)
        self.assertEqual((self.project/'main.py').read_text(),'');self.assertFalse((self.guests[0].workspace.root/'main.py').exists())
        review=self.team.request({'action':'review'});self.assertTrue(any(x['kind']=='rename' for x in review['events']));self.assertTrue(any(x['path']=='src/renamed.py' and 'offline edit' in x['diff'] for x in review['changes']))
    def test_permitted_stations_share_one_execution_and_evicted_retry_cannot_restart(self):
        self.role(0,'runner');self.role(1,'runner')
        with ThreadPoolExecutor(max_workers=6) as pool:runs=list(pool.map(lambda i:self.guests[i%2].features.team.request({'action':'run','path':'main.py','requestId':'intent-'+str(i)}),range(6)))
        self.assertEqual(len({x['job'] for x in runs}),1);job=self.host.runner.jobs[runs[0]['job']];deadline=time.monotonic()+10
        while not job.done and time.monotonic()<deadline:time.sleep(.03)
        self.assertEqual(job.code,0,job.output);self.assertEqual((self.project/'starts.txt').read_text(),'START\n');self.assertTrue(all(not guest.runner.jobs for guest in self.guests))
        self.team.room.run_requests.pop('intent-0')
        with self.assertRaisesRegex(ValueError,'reintento'):self.guests[0].features.team.request({'action':'run','path':'main.py','requestId':'intent-0'})
        self.assertEqual(len(self.host.runner.jobs),1)

if __name__=='__main__':unittest.main()
