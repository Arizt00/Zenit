"""Real TCP fault relay on ONE station; this is not physical LAN/Internet QA."""
import hashlib,json,socket,tempfile,threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from pycrdt import Doc,Text
from backend.server import Application
from backend.team import encode,decode

ROOT=Path(__file__).resolve().parents[1]

class FaultRelay:
    def __init__(self,invitation):
        self.upstream,self.token=invitation.split('#');self.drop={};self.delay=0;self.requests=[];self.lock=threading.Lock()
        relay=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']));body=json.loads(raw);action=body.get('action','sync')
                with relay.lock:
                    relay.requests.append(body);drop=relay.drop.get(action,0)>0
                    if drop:relay.drop[action]-=1
                time.sleep(relay.delay)
                req=Request(relay.upstream+'v1',data=raw,headers={'Authorization':self.headers['Authorization'],'Content-Type':'application/json'},method='POST')
                try:
                    with build_opener(ProxyHandler({})).open(req,timeout=8) as response:result=response.read();status=response.status
                except Exception as error:
                    if not hasattr(error,'read'):raise
                    result=error.read();status=error.code
                if drop:
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                self.send_response(status);self.send_header('Content-Length',str(len(result)));self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(result)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.invitation=f'http://127.0.0.1:{self.server.server_port}/#{self.token}'
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(3)

class CoCoRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'host';self.project.mkdir();(self.project/'src').mkdir()
        (self.project/'main.py').write_text('import os,time\nwith open("starts.txt","a") as f:f.write(str(os.getpid())+"\\n")\nprint("ONE_PROCESS",flush=True)\ntime.sleep(.3)\n')
        (self.project/'src/shared.py').write_text('VALUE = 42\n');self.host=Application(ROOT,self.project,data_dir=self.base/'host-profile');self.host.workspace.trusted=True;self.team=self.host.features.team
        invitation=self.team.start(self.host.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]})['invitation'];self.relay=FaultRelay(invitation);self.guests=[]
    def tearDown(self):
        self.relay.close()
        for guest in self.guests:guest.features.shutdown();guest.runner.shutdown()
        self.host.features.shutdown();self.host.runner.shutdown();self.temp.cleanup()
    def guest(self):
        index=len(self.guests);folder=self.base/('guest'+str(index));folder.mkdir();app=Application(ROOT,folder,data_dir=self.base/('guest-profile'+str(index)));app.workspace.trusted=True;self.guests.append(app);return app.features.team
    def join(self,guest):return guest.join(guest.features.app.workspace,self.relay.invitation)
    def role(self,guest,role):
        peer=guest.request({'action':'sync','vectors':{}})['self']['id'];self.team.request({'action':'permissions','participant':peer,'role':role});return peer
    def wait(self,job):
        task=self.host.runner.jobs[job];deadline=time.monotonic()+12
        while not task.done and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(task.done);self.assertEqual(task.code,0,task.output);return task
    def test_lost_initial_responses_reconnect_same_identity_and_permissions(self):
        guest=self.guest();self.relay.drop['sync']=2
        with self.assertRaisesRegex(ValueError,'identidad'):self.join(guest)
        self.assertEqual(len(self.team.room.project.members),1);peer=next(iter(self.team.room.project.members));self.team.request({'action':'permissions','participant':peer,'role':'editor'})
        state=self.join(guest);sync=guest.request({'action':'sync','vectors':{}})
        self.assertEqual(state['room'],self.team.room.id);self.assertEqual(sync['self']['id'],peer);self.assertEqual(sync['self']['role'],'editor');self.assertEqual(len([m for m in self.team.room.project.members.values() if m['role']!='host']),1)
        with self.assertRaises(PermissionError):self.team.room.request({'action':'sync','peer':peer,'resumeKey':'x'*43,'vectors':{}})
    def test_reset_after_start_retries_after_completion_without_second_process_and_traces_source(self):
        guest=self.guest();self.join(guest);self.role(guest,'runner');self.relay.drop['run']=2
        with self.assertRaises(ValueError):guest.request({'action':'run','path':'main.py','requestId':'survives-reset'})
        run=next(iter(self.team.room.run_requests.values()));job=self.wait(run['job']);self.assertEqual(len((self.project/'starts.txt').read_text().splitlines()),1)
        self.join(guest);recovered=guest.request({'action':'run','path':'main.py','requestId':'survives-reset'});self.assertEqual(recovered['job'],job.id);self.assertTrue(recovered['reused'])
        origin=guest.request({'action':'evidence','job':job.id});self.assertTrue(origin['sourceMatches']);self.assertTrue(origin['environmentMatches']);self.assertEqual(origin['sourceSha256'],hashlib.sha256((self.project/'main.py').read_text().encode()).hexdigest());self.assertEqual(origin['outputSha256'],hashlib.sha256(job.output.encode()).hexdigest());self.assertEqual(origin['commands'],job.commands)
        self.team.room.documents['main.py']['text'].insert(0,'# UNSAVED\n');stale=guest.request({'action':'evidence','job':job.id});self.assertFalse(stale['sourceMatches']);self.assertTrue(stale['savedSourceMatches']);self.assertFalse(stale['sharedSourceMatches'])
        (self.project/'main.py').write_text('print("CHANGED")\n');self.assertFalse(guest.request({'action':'evidence','job':job.id})['sourceMatches']);self.assertEqual(guest.request({'action':'run','path':'main.py','requestId':'survives-reset'})['job'],job.id)
        self.assertEqual(len(self.host.runner.jobs),1);self.assertFalse(guest.features.app.runner.jobs)
    def test_latency_merge_tree_permission_downgrade_and_concurrent_run(self):
        first=self.guest();second=self.guest();self.join(first);self.join(second);self.role(first,'runner');self.role(second,'runner');self.relay.delay=.06
        first.request({'action':'project-open','path':'src/shared.py'});state=first.request({'action':'sync','vectors':{}});copies=[]
        for text in ('# FIRST\n','# SECOND\n'):
            doc=Doc({'text':Text()});doc.apply_update(decode(state['updates']['src/shared.py']));before=doc.get_state();doc['text'].insert(0,text);copies.append(encode(doc.get_update(before)))
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda pair:pair[0].request({'action':'sync','vectors':{},'updates':{'src/shared.py':pair[1]}}),zip((first,second),copies)))
        original_id=self.team.room.project.document_ids['src/shared.py'];first.request({'action':'project-rename','path':'src/shared.py','newPath':'src/renamed.py'});updated=second.request({'action':'sync','vectors':{}});shared=Doc({'text':Text()});shared.apply_update(decode(updated['updates']['src/renamed.py']));self.assertIn('# FIRST',str(shared['text']));self.assertIn('# SECOND',str(shared['text']));self.assertEqual(self.team.room.project.document_ids['src/renamed.py'],original_id)
        self.role(second,'viewer');before=shared.get_state();shared['text'].insert(0,'# DENIED\n');blocked=second.request({'action':'sync','vectors':{},'updates':{'src/renamed.py':encode(shared.get_update(before))}});self.assertFalse(blocked['acceptedUpdates']);self.assertNotIn('DENIED',str(self.team.room.documents['src/renamed.py']['text']))
        for action in ({'action':'run','path':'main.py','requestId':'denied'},{'action':'project-create','path':'denied.py'},{'action':'save','path':'main.py'}):
            with self.assertRaises(ValueError):second.request(action)
        self.role(second,'runner')
        with ThreadPoolExecutor(max_workers=2) as pool:runs=list(pool.map(lambda pair:pair[0].request({'action':'run','path':'main.py','requestId':pair[1]}),((first,'first-run'),(second,'second-run'))))
        self.assertEqual(runs[0]['job'],runs[1]['job']);self.wait(runs[0]['job']);self.assertEqual(len((self.project/'starts.txt').read_text().splitlines()),1)
        with self.assertRaisesRegex(ValueError,'otra estación'):second.request({'action':'run','path':'main.py','requestId':'first-run'})
        self.assertFalse((self.guests[1].workspace.root/'src/renamed.py').exists());self.assertFalse(self.guests[1].runner.jobs)

    def test_lost_tree_mutation_responses_are_replayed_once_and_cannot_change_payload(self):
        guest=self.guest();self.join(guest);self.role(guest,'editor');self.relay.drop['project-create']=2
        create={'action':'project-create','path':'src/new.py','text':'print(42)\n','operationId':'create-one'}
        with self.assertRaises(ValueError):guest.request(create)
        created=guest.request(create);self.assertTrue(created['reused']);self.assertEqual(len([e for e in self.team.room.project.events if e['kind']=='create']),1)
        with self.assertRaisesRegex(ValueError,'cambió la operación'):guest.request({**create,'text':'different'})
        self.relay.drop['project-rename']=1;renamed=guest.request({'action':'project-rename','path':'src/new.py','newPath':'src/moved.py','operationId':'rename-one'});self.assertTrue(renamed['reused']);self.assertEqual(renamed['id'],created['id']);self.assertFalse((self.project/'src/new.py').exists());self.assertTrue((self.project/'src/moved.py').is_file())
        self.role(guest,'viewer')
        with self.assertRaises(ValueError):guest.request(create)

    def test_slow_requests_are_bounded_without_limiting_participant_identities(self):
        from urllib.parse import urlsplit
        from backend.team import TeamService
        url=urlsplit(self.team.url);connections=[]
        try:
            for _ in range(16):
                connection=socket.create_connection((url.hostname,url.port),timeout=2);connections.append(connection);connection.sendall(('POST /v1 HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer '+url.fragment+'\r\nContent-Length: 100\r\n\r\n').encode())
            deadline=time.monotonic()+3
            while self.team.pending_requests<16 and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(self.team.pending_requests,16)
            with self.assertRaisesRegex(ValueError,'ocupada'):TeamService(None).contact((url._replace(fragment='',path='/v1').geturl(),url.fragment),{'action':'sync','peer':'later','resumeKey':'a'*43,'vectors':{}})
        finally:
            for connection in connections:connection.close()
        deadline=time.monotonic()+3
        while self.team.pending_requests and time.monotonic()<deadline:time.sleep(.02)
        self.assertEqual(self.team.pending_requests,0);guest=self.guest();self.join(guest);self.assertEqual(len(self.team.room.project.members),1)
if __name__=='__main__':unittest.main()
