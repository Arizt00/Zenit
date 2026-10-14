import tempfile,unittest
from pathlib import Path
from backend.preferences import Preferences
from backend.extensions import ExtensionStore
from backend.factory_extensions import install_factory
ROOT=Path(__file__).resolve().parents[1]

class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.prefs=Preferences(Path(self.tmp.name));self.store=ExtensionStore(self.prefs)
    def test_original_nc_package_installs_declarations_once_without_changing_preferences(self):
        self.prefs.update({'appearance.iconTheme':'zenit'});before=self.prefs.path.read_bytes();items=install_factory(self.store,ROOT);self.assertEqual([x['id'] for x in items],['nc-lang.nc-language']);self.assertEqual(self.prefs.path.read_bytes(),before)
        c=self.store.contributions();self.assertTrue(any(x['owner']=='nc-lang.nc-language' for x in c['grammars']));self.assertTrue(c['snippets']);self.assertEqual(install_factory(self.store,ROOT),[])
    def test_factory_respects_user_removal(self):
        install_factory(self.store,ROOT);self.store.update_state('nc-lang.nc-language',remove=True);self.assertEqual(install_factory(self.store,ROOT),[]);self.assertNotIn('nc-lang.nc-language',self.store.installed)
    def test_existing_version_is_preserved(self):
        package=ROOT/'web/assets/extensions/nc-language-1.0.0-21v.vsix';r=self.store.inspect_local(str(package));self.store.install(r['ticket'],True);before=self.store.index.read_bytes();self.assertEqual(install_factory(self.store,ROOT),[]);self.assertEqual(self.store.index.read_bytes(),before)
    def test_actual_nc_engine_registers_language_features_without_unsupported_api_calls(self):
        from backend.server import Application
        ws=Path(self.tmp.name)/'project';ws.mkdir();text='stc main() { return 0; }\n';(ws/'main.nc').write_text(text)
        app=Application(ROOT,ws,data_dir=Path(self.tmp.name)/'native-profile');app.workspace.trusted=True
        try:
            install_factory(app.features.extensions,ROOT);runtime=app.features.extension_runtime;state=runtime.start(app.workspace,'nc-lang.nc-language',True);host=state['hosts'][0]
            self.assertTrue(host['running']);self.assertFalse(host['unsupportedApis']);kinds={p['kind'] for p in host['providers']};self.assertTrue({'hover','completion','symbols','semantic','rename','format'}.issubset(kinds),kinds)
            result=runtime.request(app.workspace,{'id':'nc-lang.nc-language','method':'provide','kind':'semantic','document':{'path':'main.nc','text':text,'language':'nc'}})
            self.assertTrue(result['items']);self.assertTrue(result['items'][0]['data'])
        finally:app.features.shutdown();app.runner.shutdown()

if __name__=='__main__':unittest.main()
