"""Ship the reviewed nC update without replacing custom/removed/disabled choices."""
import json,tempfile,unittest
from pathlib import Path
from backend.server import Application
from backend.factory_extensions import install_factory
from backend.extension_dependencies import dependency_graph

ROOT=Path(__file__).resolve().parents[1]
EID='nc-lang.nc-language'
class FactoryUpgradeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.base=Path(self.temp.name);project=self.base/'project';project.mkdir();(project/'main.n').write_text('// keep project')
  self.app=Application(ROOT,project,data_dir=self.base/'profile');self.f=self.app.features;self.store=self.f.extensions
  self.store.install(self.store.inspect_file(ROOT/'web/assets/extensions/nc-language-1.0.0-21v.zenit.6.vsix')['ticket'],True)
  (self.f.prefs.directory/'factory-extensions.json').write_text(json.dumps({EID:'existing'}));self.f.prefs.update({'appearance.theme':'dark'})
 def tearDown(self):self.f.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def test_exact_shipped_digest_upgrades_and_keeps_settings_and_runtime_data(self):
  runtime_data=self.store.root/'.runtime-data'/EID/'configuration.json';runtime_data.parent.mkdir(parents=True);runtime_data.write_text('{"nc.enableDiagnostics":false}')
  result=install_factory(self.store,ROOT);self.assertEqual(len(result),1);self.assertEqual(result[0]['version'],'1.0.0-21v.zenit.7');self.assertIn('_factoryPrevious',result[0]);self.assertEqual(self.f.prefs.get('appearance.theme'),'dark');self.assertEqual(runtime_data.read_text(),'{"nc.enableDiagnostics":false}');self.assertEqual((self.app.workspace.root/'main.n').read_text(),'// keep project');self.assertEqual(install_factory(self.store,ROOT),[])
 def test_disabled_extension_remains_disabled(self):
  self.store.update_state(EID,enabled=False);result=install_factory(self.store,ROOT);self.f.extension_runtime.migrate_factory_approvals(result);self.assertFalse(self.store.installed[EID]['enabled'])
 def test_removed_extension_is_not_reinstalled(self):
  self.store.update_state(EID,remove=True);self.assertEqual(install_factory(self.store,ROOT),[]);self.assertNotIn(EID,self.store.installed)
 def test_custom_package_digest_is_not_replaced(self):
  record=self.store.installed[EID];record['sha256']='a'*64
  from backend.preferences import atomic_json
  atomic_json(self.store.index,self.store.installed);self.assertEqual(install_factory(self.store,ROOT),[]);self.assertEqual(self.store.installed[EID]['version'],'1.0.0-21v.zenit.6')
 def test_existing_single_package_approval_migrates_without_new_workspace_permissions(self):
  runtime=self.f.extension_runtime;ws=self.app.workspace;runtime.approve(ws,EID,dependency_graph(self.store,EID));result=install_factory(self.store,ROOT);runtime.migrate_factory_approvals(result)
  self.assertEqual(runtime.graph_approvals[str(ws.root)][EID],runtime.graph_signature(dependency_graph(self.store,EID)));self.assertEqual(len(runtime.approvals),1)
 def test_approval_with_a_different_graph_stays_subject_to_review(self):
  runtime=self.f.extension_runtime;ws=self.app.workspace;runtime.approve(ws,EID,dependency_graph(self.store,EID));runtime.graph_approvals[str(ws.root)][EID]='unreviewed-graph';result=install_factory(self.store,ROOT);runtime.migrate_factory_approvals(result)
  self.assertEqual(runtime.graph_approvals[str(ws.root)][EID],'unreviewed-graph')

if __name__=='__main__':unittest.main()
