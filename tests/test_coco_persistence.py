"""Durable edits, identities and side-effect reservations across host restarts."""
import hashlib
import os
from pathlib import Path
import sqlite3
import json
import subprocess
import socket
from urllib.parse import urlsplit
import tempfile
import time
import unittest
from contextlib import closing
from unittest.mock import patch
from pycrdt import Doc,Text
from backend.server import Application
from backend.team import encode,decode

ROOT=Path(__file__).resolve().parents[1]


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.ws=self.base/'project';self.ws.mkdir();self.guest_ws=self.base/'guest';self.guest_ws.mkdir()
        (self.ws/'main.py').write_text('with open("starts.txt","a") as stream:stream.write("START\\n")\nprint("ONE_RUN",flush=True)\n',encoding='utf-8')
        self.apps=[];self.host=self.make(self.ws,'host-profile');self.guest=self.make(self.guest_ws,'guest-profile')
        self.team=self.host.features.team
        self.invite=self.team.start(self.host.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'}]})['invitation']
        self.guest.features.team.join(self.guest.workspace,self.invite)
        self.peer=self.guest.features.team.request({'action':'sync','vectors':{}})['self']['id']
        self.team.request({'action':'permissions','participant':self.peer,'role':'runner'})

    def make(self,workspace,profile):
        app=Application(ROOT,workspace,data_dir=self.base/profile);app.workspace.trusted=True;self.apps.append(app);return app

    def close(self,app):
        app.features.shutdown();app.runner.shutdown();self.apps.remove(app)

    def restart(self):
        self.close(self.host);self.host=self.make(self.ws,'host-profile');self.team=self.host.features.team
        self.assertIsNone(self.team.room);self.assertIsNone(self.team.server)
        self.assertTrue(self.team.status()['recovery']['available'])
        return self.team.recover(self.host.workspace)

    def wait(self,identity):
        deadline=time.monotonic()+12
        job=self.host.runner.jobs[identity]
        while not job.done and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(job.done)
        self.team.request({'action':'job','job':identity})
        return job

    def tearDown(self):
        for app in self.apps[::-1]:app.features.shutdown();app.runner.shutdown()
        self.temp.cleanup()

    def test_restart_recovers_crdt_permissions_checkpoints_aliases_and_completed_output(self):
        guest=self.guest.features.team
        state=guest.request({'action':'sync','vectors':{}});room=state['room'];doc=Doc({'text':Text()});doc.apply_update(decode(state['updates']['main.py']))
        before=doc.get_state();doc['text'].insert(0,'# 未保存 · café\n')
        guest.request({'action':'sync','vectors':{},'updates':{'main.py':encode(doc.get_update(before))}})
        checkpoint=self.team.request({'action':'checkpoint','label':'Before rename'})
        operation={'action':'project-rename','path':'main.py','newPath':'src/renamed.py','operationId':'rename-once'}
        result=guest.request(operation)
        run=guest.request({'action':'run','path':'src/renamed.py','requestId':'run-once'});job=self.wait(run['job']);original_output=job.output
        # More uncommitted work must remain separate from the saved run's source.
        before=doc.get_state();doc['text'].insert(0,'# OFFLINE\n')
        document_id=result['id']
        guest.request({'action':'sync','vectors':{},'documentIds':{'main.py':document_id},'updates':{'main.py':encode(doc.get_update(before))}})
        restored=self.restart();self.assertEqual(restored['room'],room);self.assertEqual(restored['invitation'],self.invite)
        state=guest.request({'action':'sync','vectors':{}});self.assertEqual(state['self']['id'],self.peer);self.assertEqual(state['self']['role'],'runner')
        self.assertEqual(self.team.room.project.document_ids['src/renamed.py'],document_id)
        self.assertIn('OFFLINE',str(self.team.room.documents['src/renamed.py']['text']))
        self.assertNotIn('OFFLINE',(self.ws/'src/renamed.py').read_text(encoding='utf-8'))
        self.assertEqual(self.team.room.checkpoints[0]['id'],checkpoint['id'])
        self.assertTrue(guest.request(operation)['reused'])
        retry=guest.request({'action':'run','path':'src/renamed.py','requestId':'run-once'})
        self.assertEqual(retry['job'],run['job']);self.assertFalse(self.host.runner.jobs)
        output=guest.request({'action':'job','job':run['job']});self.assertEqual(output['output'],original_output);self.assertEqual(output['code'],0)
        origin=guest.request({'action':'evidence','job':run['job']});self.assertFalse(origin['sourceMatches']);self.assertTrue(origin['savedSourceMatches'])
        self.assertEqual((self.ws/'starts.txt').read_text(),'START\n')
        self.assertTrue(guest.request({'action':'project-rename','path':'main.py','newPath':'src/renamed.py','operationId':'rename-once'})['reused'])

    def test_guest_backend_restarts_with_the_same_identity_and_downgraded_permissions(self):
        self.team.request({'action':'permissions','participant':self.peer,'role':'viewer'})
        self.close(self.guest);self.guest=self.make(self.guest_ws,'guest-profile')
        team=self.guest.features.team;self.assertTrue(team.status()['recovery']['guest'])
        team.recover(self.guest.workspace);state=team.request({'action':'sync','vectors':{}})
        self.assertEqual(state['self']['id'],self.peer);self.assertEqual(state['self']['role'],'viewer')
        with self.assertRaises(ValueError):team.request({'action':'run','path':'main.py','requestId':'denied'})

    def test_occupied_port_changes_address_without_changing_room_or_guest_identity(self):
        room=self.team.room.id;port=urlsplit(self.invite).port;self.close(self.host)
        with socket.socket() as occupied:
            occupied.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);occupied.bind(('127.0.0.1',port));occupied.listen()
            self.host=self.make(self.ws,'host-profile');self.team=self.host.features.team
            state=self.team.recover(self.host.workspace)
            self.assertEqual(state['room'],room);self.assertNotEqual(urlsplit(state['invitation']).port,port)
            self.guest.features.team.join(self.guest.workspace,state['invitation'])
            result=self.guest.features.team.request({'action':'sync','vectors':{}})
            self.assertEqual(result['self']['id'],self.peer);self.assertEqual(result['self']['role'],'runner')

    def test_evicted_intent_stays_a_tombstone_after_restart_and_private_credentials_are_protected(self):
        guest=self.guest.features.team;run=guest.request({'action':'run','path':'main.py','requestId':'tombstone'});self.wait(run['job'])
        self.team.room.run_requests.pop('tombstone');self.team.room.persist()
        if os.name=='nt':
            raw=self.team.store.path.read_bytes()
            self.assertNotIn(self.team.room.token.encode(),raw)
            self.assertNotIn(guest.remote_identity['resumeKey'].encode(),raw)
        self.restart()
        with self.assertRaisesRegex(ValueError,'reintento'):guest.request({'action':'run','path':'main.py','requestId':'tombstone'})
        self.assertFalse(self.host.runner.jobs);self.assertEqual((self.ws/'starts.txt').read_text(),'START\n')

    def test_recovered_console_tail_preserves_absolute_offsets_for_existing_observers(self):
        doc=self.team.room.documents['main.py'];doc['text'].clear();doc['text'].insert(0,'print("x"*120000)\n');self.team.room.persist(['main.py'])
        guest=self.guest.features.team;run=guest.request({'action':'run','path':'main.py','requestId':'large'});job=self.wait(run['job']);output=job.output
        self.restart();offset=0;tail=''
        while True:
            result=guest.request({'action':'job','job':run['job'],'offset':offset});tail+=result['output'];offset=result['offset']
            self.assertTrue(result['truncated'])
            if not result['more']:break
        self.assertEqual(tail,output[-100000:]);self.assertEqual(offset,len(output))
        observer=guest.request({'action':'job','job':run['job'],'offset':len(output)-10})
        self.assertEqual(observer['output'],output[-10:]);self.assertEqual(observer['offset'],len(output))

    def test_recovered_evidence_invalidates_changed_descriptors_runtime_and_package_metadata(self):
        (self.ws/'requirements.txt').write_text('sample==1.0\n')
        metadata=self.ws/'.venv/Lib/site-packages/sample-1.0.dist-info/METADATA';metadata.parent.mkdir(parents=True);metadata.write_text('Name: sample\nVersion: 1.0\n')
        guest=self.guest.features.team;run=guest.request({'action':'run','path':'main.py','requestId':'context'});self.wait(run['job']);self.restart()
        original=guest.request({'action':'evidence','job':run['job']});self.assertTrue(original['environmentMatches']);self.assertNotEqual(original['contextVerification']['status'],'changed')
        (self.ws/'requirements.txt').write_text('sample==2.0\n')
        metadata.write_text('Name: sample\nVersion: 2.0\n')
        self.host.features.runtimes.config['testChangedTarget']='another-target'
        changed=guest.request({'action':'evidence','job':run['job']});self.assertFalse(changed['environmentMatches']);self.assertEqual(changed['contextVerification']['status'],'changed')
        self.assertIn('requirements.txt',changed['contextVerification']['changed']);self.assertTrue(changed['sourceMatches'])
        self.assertEqual(guest.request({'action':'run','path':'main.py','requestId':'context'})['job'],run['job']);self.assertFalse(self.host.runner.jobs)

    def test_local_copies_remain_private_durable_and_available_after_ending_the_room(self):
        body={'action':'preserve','room':self.team.room.id,'document':self.team.room.project.document_ids['main.py'],'path':'main.py','text':'# LOCAL_UNCONFIRMED\n'}
        metadata=self.team.local_draft(body);self.assertNotIn('text',metadata)
        self.assertEqual(self.team.local_draft(body)['id'],metadata['id'])
        self.restart();copies=self.team.store.local_drafts(self.ws);self.assertEqual(len(copies),1)
        self.assertEqual(self.team.local_draft({'action':'read','id':metadata['id']})['text'],body['text'])
        self.assertFalse(self.guest.features.team.store.local_drafts(self.guest_ws))
        self.team.stop();self.assertEqual(len(self.team.store.local_drafts(self.ws)),1)
        self.team.local_draft({'action':'discard','id':metadata['id']});self.assertFalse(self.team.store.local_drafts(self.ws))

    def test_interrupted_work_requires_host_review_and_does_not_reexecute_the_original_intent(self):
        with patch.object(self.host.features.runtimes,'plan',return_value={'commands':[[os.sys.executable,'-u','-c','import time;print("PARTIAL",flush=True);time.sleep(30)']]}):
            run=self.guest.features.team.request({'action':'run','path':'main.py','requestId':'interrupted'})
        job=self.host.runner.jobs[run['job']];deadline=time.monotonic()+8
        while 'PARTIAL' not in job.output and time.monotonic()<deadline:time.sleep(.02)
        self.assertIn('PARTIAL',job.output)
        self.restart()
        guest=self.guest.features.team;retry=guest.request({'action':'run','path':'main.py','requestId':'interrupted'})
        self.assertEqual(retry['job'],run['job']);self.assertTrue(retry['interrupted']);self.assertFalse(self.host.runner.jobs)
        self.assertIn('PARTIAL',guest.request({'action':'job','job':run['job']})['output'])
        with self.assertRaisesRegex(ValueError,'interrumpida'):guest.request({'action':'run','path':'main.py','requestId':'new'})
        with self.assertRaises(ValueError):guest.request({'action':'acknowledge-interruption','job':run['job']})
        self.team.request({'action':'acknowledge-interruption','job':run['job']})
        fresh=guest.request({'action':'run','path':'main.py','requestId':'new'});self.wait(fresh['job'])
        self.assertNotEqual(fresh['job'],run['job']);self.assertEqual((self.ws/'starts.txt').read_text(),'START\n')

    def test_failed_durable_reservation_never_starts_a_process(self):
        with patch.object(self.team.store,'save',side_effect=OSError('Injected disk failure')):
            with self.assertRaises(ValueError):self.guest.features.team.request({'action':'run','path':'main.py','requestId':'disk-full'})
        self.assertFalse(self.host.runner.jobs);self.assertFalse((self.ws/'starts.txt').exists())

    def test_ambiguous_tree_mutation_is_reserved_before_the_filesystem_changes(self):
        original=self.team.store.save;calls=[]
        def lost_commit(room,paths=()):
            calls.append(1)
            if len(calls)>1:raise OSError('Injected crash between rename and checkpoint')
            return original(room,paths)
        with patch.object(self.team.store,'save',side_effect=lost_commit):
            with self.assertRaises(ValueError):self.guest.features.team.request({'action':'project-rename','path':'main.py','newPath':'renamed.py','operationId':'ambiguous'})
        # Simulate process loss: discard live state without another checkpoint.
        self.team.room.revoked=True;self.close(self.host);self.host=self.make(self.ws,'host-profile');self.team=self.host.features.team;self.team.recover(self.host.workspace)
        with self.assertRaisesRegex(ValueError,'reintento'):self.guest.features.team.request({'action':'project-rename','path':'main.py','newPath':'renamed.py','operationId':'ambiguous'})
        self.assertTrue((self.ws/'renamed.py').exists());self.assertFalse((self.ws/'main.py').exists())
        recovery=self.team.request({'action':'sync','vectors':{}})['recovery'];self.assertTrue(recovery['pendingOperations']);self.assertIn('main.py',recovery['conflicts'])

    def test_end_revokes_recovery_and_idle_sync_does_not_rewrite_the_checkpoint(self):
        guest=self.guest.features.team
        with patch.object(self.team.store,'save',wraps=self.team.store.save) as save:
            for _ in range(4):guest.request({'action':'sync','vectors':{}})
            self.assertEqual(save.call_count,0)
        self.team.stop();self.assertIsNone(self.team.store.load(self.ws));self.close(self.host)
        self.host=self.make(self.ws,'host-profile');self.team=self.host.features.team
        self.assertIsNone(self.team.status()['recovery'])
        with self.assertRaises(ValueError):self.team.recover(self.host.workspace)

    def test_corruption_and_external_edits_do_not_overwrite_the_project(self):
        original=(self.ws/'main.py').read_text();self.close(self.host)
        (self.ws/'main.py').write_text('# EXTERNAL\n'+original)
        self.host=self.make(self.ws,'host-profile');self.team=self.host.features.team;self.host.workspace.trusted=False
        with self.assertRaises(PermissionError):self.team.recover(self.host.workspace)
        self.host.workspace.trusted=True;self.team.recover(self.host.workspace)
        state=self.team.request({'action':'sync','vectors':{}});self.assertIn('main.py',state['recovery']['conflicts'])
        with self.assertRaisesRegex(ValueError,'fuera'):self.team.request({'action':'save','path':'main.py'})
        self.assertEqual((self.ws/'main.py').read_text(),'# EXTERNAL\n'+original)
        self.team.suspend()
        with closing(sqlite3.connect(self.team.store.path)) as connection:
            with connection:connection.execute('UPDATE rooms SET data=?',(b'corrupt',))
        self.assertIn('error',self.team.status()['recovery']);self.assertTrue(self.team.store.path.exists())

    def test_another_live_backend_cannot_recover_or_revoke_the_same_host(self):
        other=self.make(self.ws,'host-profile')
        with self.assertRaisesRegex(ValueError,'Otra instancia'):other.features.team.recover(other.workspace)
        with self.assertRaisesRegex(ValueError,'Otra instancia'):other.features.team.stop()
        self.assertIsNone(other.features.team.room)
        self.assertTrue(self.guest.features.team.request({'action':'sync','vectors':{}})['room'])

    def test_real_process_crash_preserves_session_and_detects_the_surviving_program(self):
        import psutil
        self.close(self.host);workers=[]
        def spawn():
            worker=subprocess.Popen([os.sys.executable,str(ROOT/'tests/fixtures/coco_restart_host.py'),str(self.ws),str(self.base/'host-profile')],
                                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            workers.append(worker);return worker
        def command(worker,command,**body):
            worker.stdin.write(json.dumps({'command':command,**body})+'\n');worker.stdin.flush()
            result=json.loads(worker.stdout.readline());self.assertNotIn('error',result)
            return result['result']
        child_identity=None
        try:
            worker=spawn();state=command(worker,'start');guest=self.guest.features.team
            guest.join(self.guest.workspace,state['invitation']);peer=guest.request({'action':'sync','vectors':{}})['self']['id']
            command(worker,'owner',action='permissions',participant=peer,role='runner')
            # This saved fixture deliberately outlives its backend when killed.
            text='import os,time\nwith open("starts.txt","a") as stream:stream.write(str(os.getpid())+"\\n")\nprint("SURVIVES_HOST",flush=True)\ntime.sleep(40)\n'
            shared=guest.request({'action':'sync','vectors':{}});doc=Doc({'text':Text()});doc.apply_update(decode(shared['updates']['main.py']));before=doc.get_state();doc['text'].clear();doc['text'].insert(0,text)
            guest.request({'action':'sync','vectors':{},'updates':{'main.py':encode(doc.get_update(before))}})
            run=guest.request({'action':'run','path':'main.py','requestId':'host-crash'})
            deadline=time.monotonic()+10
            while not (self.ws/'starts.txt').exists() and time.monotonic()<deadline:time.sleep(.02)
            child=psutil.Process(int((self.ws/'starts.txt').read_text().strip()));child_identity=(child.pid,child.create_time())
            time.sleep(1.05);self.assertIn('SURVIVES_HOST',guest.request({'action':'job','job':run['job']})['output'])
            worker.kill();worker.wait(timeout=8)
            replacement=spawn();self.assertTrue(command(replacement,'status')['recovery']['available'])
            recovered=command(replacement,'recover');self.assertEqual(recovered['invitation'],state['invitation'])
            self.assertEqual(recovered['room'],shared['room'])
            snapshot=guest.request({'action':'sync','vectors':{}});self.assertEqual(snapshot['self']['id'],peer);self.assertEqual(snapshot['self']['role'],'runner')
            interrupted=snapshot['recovery']['interruptions'];self.assertTrue(interrupted[0]['processAlive'])
            retry=guest.request({'action':'run','path':'main.py','requestId':'host-crash'});self.assertEqual(retry['job'],run['job']);self.assertTrue(retry['interrupted'])
            self.assertEqual(len((self.ws/'starts.txt').read_text().splitlines()),1)
            with self.assertRaisesRegex(ValueError,'interrumpida'):guest.request({'action':'run','path':'main.py','requestId':'new-before-review'})
            command(replacement,'owner',action='acknowledge-interruption',job=run['job'],stop=True)
            self.assertFalse(psutil.pid_exists(child.pid));command(replacement,'close')
        finally:
            for worker in workers:
                if worker.poll() is None:worker.kill();worker.wait(timeout=8)
                for stream in (worker.stdin,worker.stdout,worker.stderr):stream.close()
            if child_identity:
                try:
                    child=psutil.Process(child_identity[0])
                    if child.create_time()==child_identity[1]:child.kill();child.wait(timeout=5)
                except psutil.Error:pass


if __name__=='__main__':unittest.main()
