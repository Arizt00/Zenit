"""Concurrent stations observe one host process and idempotent run requests."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time
import unittest
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]


class SharedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();base=Path(self.temp.name);self.ws=base/'host';self.ws.mkdir()
        (self.ws/'main.py').write_text('import os,time\nwith open("starts.txt","a") as f:f.write(str(os.getpid())+"\\n")\nprint("SHARED_EXECUTION",flush=True)\ntime.sleep(.7)\n',encoding='utf-8')
        self.host=Application(ROOT,self.ws,data_dir=base/'host-profile');self.host.workspace.trusted=True
        self.team=self.host.features.team;self.invite=self.team.start(self.host.workspace,{'documents':[{'path':'main.py'}],'allowRun':True})['invitation']
        self.guests=[]
        for i in range(2):
            folder=base/('guest'+str(i));folder.mkdir();guest=Application(ROOT,folder,data_dir=base/('profile'+str(i)));guest.workspace.trusted=True;guest.features.team.join(guest.workspace,self.invite);self.guests.append(guest)
    def tearDown(self):
        for guest in self.guests:guest.features.shutdown();guest.runner.shutdown()
        self.host.features.shutdown();self.host.runner.shutdown();self.temp.cleanup()
    def wait(self,identity):
        job=self.host.runner.jobs[identity];deadline=time.monotonic()+10
        while not job.done and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(job.done);self.assertEqual(job.code,0);return job
    def test_concurrent_requests_share_one_process_and_lost_ack_retry_never_restarts_it(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda i:self.guests[i%2].features.team.request({'action':'run','path':'main.py','requestId':'run-'+str(i)}),range(8)))
        identity=results[0]['job'];self.assertEqual({r['job'] for r in results},{identity});self.assertEqual(len(self.host.runner.jobs),1)
        job=self.wait(identity);self.assertEqual(len((self.ws/'starts.txt').read_text().splitlines()),1)
        retry=self.guests[0].features.team.request({'action':'run','path':'main.py','requestId':'run-0'})
        self.assertEqual(retry['job'],identity);self.assertEqual(len(self.host.runner.jobs),1)
        for i,guest in enumerate(self.guests):
            state=guest.features.team.request({'peer':'guest-'+str(i),'vectors':{}})
            self.assertEqual(guest.features.team.status()['room'],self.team.room.id)
            self.assertEqual(state['executions']['main.py']['job'],identity)
            self.assertTrue(state['executions']['main.py']['done'])
            self.assertEqual(guest.features.team.request({'action':'job','job':identity})['output'],job.output)
            self.assertFalse((guest.workspace.root/'main.py').exists());self.assertFalse(guest.runner.jobs)
        again=self.team.request({'action':'run','path':'main.py','requestId':'intentional-new-run'});self.assertNotEqual(again['job'],identity);self.wait(again['job'])
        self.assertEqual(len((self.ws/'starts.txt').read_text().splitlines()),2)
    def test_more_files_join_same_room_without_overwriting_shared_edits(self):
        room=self.team.room;room.documents['main.py']['text'].insert(0,'# unsaved\n')
        (self.ws/'other.py').write_text('print("SECOND_FILE")\n')
        result=self.team.request({'action':'share','documents':[{'path':'other.py'},{'path':'./main.py','text':'overwrite'}]})
        self.assertEqual(result['room'],room.id);self.assertEqual(result['paths'],['main.py','other.py']);self.assertIn('# unsaved',str(room.documents['main.py']['text']))
        guest=self.guests[0].features.team
        with self.assertRaisesRegex(ValueError,'anfitrión'):guest.request({'action':'share','documents':[{'path':'other.py'}]})
        state=guest.request({'peer':'guest','vectors':{}});self.assertEqual(set(state['paths']),{'main.py','other.py'})
        run=guest.request({'action':'run','path':'other.py','requestId':'other'});self.assertIn('SECOND_FILE',self.wait(run['job']).output)
    def test_completed_large_output_is_drained_in_pages_without_loss(self):
        room=self.team.room;room.documents['main.py']['text'].clear();room.documents['main.py']['text'].insert(0,'print("x"*120000)\n')
        run=self.team.request({'action':'run','path':'main.py','requestId':'large-output'});job=self.wait(run['job']);output='';offset=0;pages=0
        while True:
            chunk=self.guests[0].features.team.request({'action':'job','job':job.id,'offset':offset});output+=chunk['output'];offset=chunk['offset'];pages+=1
            if not chunk['more']:break
        self.assertGreater(pages,2);self.assertEqual(output,job.output)
    def test_request_identity_cannot_be_reused_for_another_file(self):
        run=self.team.request({'action':'run','path':'main.py','requestId':'same-id'})
        (self.ws/'other.py').write_text('print("different")\n');self.team.request({'action':'share','documents':[{'path':'other.py'}]})
        with self.assertRaisesRegex(ValueError,'otro archivo'):self.team.request({'action':'run','path':'other.py','requestId':'same-id'})
        self.wait(run['job']);self.assertEqual(len(self.host.runner.jobs),1)
    def test_lost_run_reply_is_retried_with_the_same_identity(self):
        from unittest.mock import patch
        from urllib.error import URLError
        from backend import team
        original=team.build_opener;calls=[]
        class Transport:
            def open(self,request,**kwargs):
                response=original().open(request,**kwargs);calls.append(request.data)
                if len(calls)==1:
                    response.read();response.close();raise URLError('Injected lost acknowledgement after execution started')
                return response
        with patch.object(team,'build_opener',return_value=Transport()):
            result=self.guests[0].features.team.request({'action':'run','path':'main.py','requestId':'lost-ack'})
        self.wait(result['job']);self.assertEqual(len(calls),2);self.assertEqual(calls[0],calls[1]);self.assertEqual(len(self.host.runner.jobs),1)
        self.assertEqual(len((self.ws/'starts.txt').read_text().splitlines()),1)


if __name__=='__main__':unittest.main()
