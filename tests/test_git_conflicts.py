import os,subprocess,tempfile,unittest
from pathlib import Path
from backend.server import Application
from backend.workspace import ConflictError
from backend.git_conflicts import GitConflicts
ROOT=Path(__file__).resolve().parents[1]

def conflicted_project(root):
    def git(*args,check=True):return subprocess.run(['git','-c','core.hooksPath='+os.devnull,'-c','user.name=Zénit QA','-c','user.email=qa@example.invalid',*args],cwd=root,capture_output=True,text=True,check=check,creationflags=0x08000000 if os.name=='nt' else 0)
    git('init','-q');branch=git('symbolic-ref','--short','HEAD').stdout.strip();(root/'main.py').write_text('print("base")\n');git('add','main.py');git('commit','-qm','fixture base');git('branch','incoming');(root/'main.py').write_text('print("ours")\n');git('commit','-qam','fixture ours');git('checkout','-q','incoming');(root/'main.py').write_text('print("theirs")\n');git('commit','-qam','fixture theirs');git('checkout','-q',branch);assert git('merge','incoming',check=False).returncode==1
    return git

class GitConflictTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir();self.git=conflicted_project(self.project);self.app=Application(ROOT,self.project,data_dir=self.base/'profile');self.app.workspace.trusted=True
    def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
    def test_three_versions_draft_recovery_and_resolve_actual_index(self):
        manager=self.app.features.conflicts;ws=self.app.workspace;self.assertEqual(manager.snapshot(ws)['files'][0]['path'],'main.py');review=manager.read(ws,'main.py');self.assertIn('"base"',review['base']);self.assertIn('"ours"',review['ours']);self.assertIn('"theirs"',review['theirs']);self.assertIn('<<<<<<<',review['result'])
        original=(self.project/'main.py').read_bytes();manager.draft(ws,{'ticket':review['ticket'],'content':'print("resolved")\n'});restored=GitConflicts(self.app.features).read(ws,'main.py');self.assertTrue(restored['draft']);self.assertEqual(restored['result'],'print("resolved")\n');self.assertEqual((self.project/'main.py').read_bytes(),original)
        result=manager.apply(ws,{'ticket':review['ticket'],'content':'print("resolved")\n','stage':True,'consent':True});self.assertTrue(result['staged']);self.assertEqual(Path(result['recovery']).read_bytes(),original);self.assertFalse(manager.snapshot(ws)['files']);self.assertIn('resolved',self.git('diff','--cached','--','main.py').stdout)
    def test_external_file_index_or_buffer_changes_are_preserved(self):
        manager=self.app.features.conflicts;ws=self.app.workspace;review=manager.read(ws,'main.py');original=(self.project/'main.py').read_bytes();(self.project/'main.py').write_text('outside edit\n')
        with self.assertRaises(ConflictError):manager.apply(ws,{'ticket':review['ticket'],'content':'overwrite','consent':True})
        self.assertEqual((self.project/'main.py').read_text(),'outside edit\n');(self.project/'main.py').write_bytes(original);review=manager.read(ws,'main.py');self.app.features.buffers.update(ws,{'path':'main.py','text':'pending buffer','saved':False})
        with self.assertRaises(ConflictError):manager.apply(ws,{'ticket':review['ticket'],'content':'overwrite','consent':True})
        self.app.features.buffers.clear();review=manager.read(ws,'main.py');self.git('add','main.py')
        with self.assertRaises(ConflictError):manager.apply(ws,{'ticket':review['ticket'],'content':'overwrite','consent':True})
        self.assertEqual((self.project/'main.py').read_bytes(),original)
    def test_unresolved_markers_cannot_be_marked_resolved(self):
        manager=self.app.features.conflicts;review=manager.read(self.app.workspace,'main.py')
        with self.assertRaisesRegex(ValueError,'marcadores'):manager.apply(self.app.workspace,{'ticket':review['ticket'],'content':review['result'],'stage':True,'consent':True})
        self.assertTrue(manager.snapshot(self.app.workspace)['files'])

if __name__=='__main__':unittest.main()
