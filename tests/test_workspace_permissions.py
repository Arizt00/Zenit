import json,tempfile,unittest
from pathlib import Path
from backend.permissions import WorkspacePermissions
from backend.server import Application
from backend.version import VERSION,REVISION
ROOT=Path(__file__).resolve().parents[1]

class WorkspacePermissionsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/'project';self.root.mkdir();self.profile=self.base/'profile';self.profile.mkdir()
 def test_grants_are_durable_private_and_exact_folder_only(self):
  p=WorkspacePermissions(self.profile);self.assertFalse(p.state(self.root)['trusted']);p.set(self.root,True);p=WorkspacePermissions(self.profile);self.assertEqual(p.state(self.root),{'trusted':True,'source':'remembered'});self.assertNotIn(str(self.root),p.path.read_text());self.assertFalse(p.state(self.root/'child')['trusted']);self.assertTrue(p.state(self.root/'.')['trusted'])
 def test_revocation_overrides_direct_mode_until_explicit_reauthorization(self):
  p=WorkspacePermissions(self.profile);self.assertEqual(p.state(self.root,True)['source'],'direct');p.set(self.root,False);p=WorkspacePermissions(self.profile);self.assertEqual(p.state(self.root,True),{'trusted':False,'source':'revoked'});p.set(self.root,True);self.assertTrue(p.state(self.root,True)['trusted'])
 def test_malformed_storage_and_non_boolean_decisions_do_not_grant(self):
  (self.profile/'workspace-permissions.json').write_text(json.dumps({'version':1,'workspaces':{'a'*64:'yes','../project':True}}));self.assertEqual(WorkspacePermissions(self.profile).decisions,{})
  for value in [1,None,'true']:
   with self.assertRaises(ValueError):WorkspacePermissions(self.profile).set(self.root,value)
 def app(self):
  app=Application(ROOT,self.root,data_dir=self.profile);self.addCleanup(app.features.shutdown);self.addCleanup(app.runner.shutdown);return app
 def test_actual_application_restores_grant_and_direct_preference_on_restart(self):
  app=self.app();self.assertFalse(app.workspace.trusted);app.features.trust(True);second=self.app();self.assertTrue(second.workspace.trusted);self.assertEqual(second.state()['trustSource'],'remembered');second.features.trust(False);third=self.app();self.assertFalse(third.workspace.trusted);third.features.post('/settings',{'settings':{'security.confirmRoutineActions':False}});self.assertFalse(third.workspace.trusted);third.features.trust(True);fourth=self.app();self.assertTrue(fourth.workspace.trusted)
 def test_direct_mode_allows_requested_actions_without_preapproving_revoked_folder(self):
  app=self.app();self.assertEqual(app.state()['version'],VERSION);self.assertEqual(app.state()['revision'],REVISION);app.features.post('/settings',{'settings':{'security.confirmRoutineActions':False}});self.assertTrue(app.workspace.trusted);self.assertEqual(app.state()['trustSource'],'direct');app.features.trust(False)
  with self.assertRaises(PermissionError):app.features._trusted()
  self.assertFalse(self.app().workspace.trusted)
