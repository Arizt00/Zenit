import json,threading,unittest
from types import SimpleNamespace
from backend.workspace import ConflictError
from tests.test_project_tests import ProjectTestTests
from tests.test_hilo_tern import wait

class MelodyVerificationTests(ProjectTestTests):
    def test_coordinated_batch_real_tests_trace_and_whole_batch_restore(self):
        p=self.app.features;ws=self.app.workspace;before={name:(self.project/name).read_text() for name in ('calc.py','tests/test_calc.py')}
        prepared=p.melody_files.prepare(ws,{'question':'Modifica calc.py y tests/test_calc.py para devolver y comprobar 43'})
        operations=[{'kind':'update','path':name,'content':content.replace('42','43').replace('41','43')} for name,content in before.items()]
        p.ai.jobs['fixture']=SimpleNamespace(file_workspace=str(ws.root),file_snapshots=prepared['fileSnapshots'],file_session=prepared['fileSession'],file_delete_allowed=False,text=json.dumps({'summary':'Actualizar función y sus pruebas','operations':operations}),done=True,error='',cancelled=threading.Event())
        plan=p.melody_files.review(ws,'fixture');self.assertEqual({x['path'] for x in plan['consulted']},set(before));receipt=p.melody_files.commit(ws,plan['ticket'],True)['receipt']
        run=p.melody_files.verify(ws,{'receipt':receipt,'framework':'unittest','consent':True})
        with self.assertRaises(ConflictError):p.melody_files.undo(ws,receipt)
        self.assertEqual(wait(p.hilo,run['job'])['state'],'done');trace=p.melody_files.trace(ws,receipt);self.assertEqual(trace['runs'][0]['result']['summary']['passed'],2);self.assertEqual(trace['runs'][0]['result']['contextChanged'],[]);self.assertTrue(trace['runs'][0]['plan']['commands'])
        p.melody_files.undo(ws,receipt)
        for name,content in before.items():self.assertEqual((self.project/name).read_text(),content)

if __name__=='__main__':unittest.main()
