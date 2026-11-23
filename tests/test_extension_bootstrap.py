import io,json,tempfile,unittest,zipfile
from pathlib import Path
from backend.server import Application
from backend.extension_bootstrap import activation_message
ROOT=Path(__file__).resolve().parents[1]

class ActivationTest(unittest.TestCase):
 def test_large_real_manifest_activates_without_relaxing_command_limit(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);ws=base/'project';ws.mkdir();app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
   manifest={'publisher':'qa','name':'large','version':'1.0.0','main':'main.cjs','description':'x'*1_100_000}
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,'w') as z:
    z.writestr('extension/package.json',json.dumps(manifest));z.writestr('extension/main.cjs',"const v=require('vscode');exports.activate=c=>v.commands.registerCommand('qa.length',()=>c.extension.packageJSON.description.length);")
   try:
    store=app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);runtime=app.features.extension_runtime
    state=runtime.start(app.workspace,'qa.large',True);self.assertTrue(state['hosts'][0]['running'])
    self.assertEqual(runtime.request(app.workspace,{'id':'qa.large','method':'command','command':'qa.length'})['result'],1_100_000)
    self.assertFalse(list((base/'profile').rglob('.activation-*.json')))
    with self.assertRaisesRegex(ValueError,'demasiado grande'):runtime.request(app.workspace,{'id':'qa.large','method':'command','command':'qa.length','arguments':['x'*2_000_001]})
    self.assertTrue(runtime.snapshot()['hosts'][0]['running'])
   finally:app.features.shutdown();app.runner.shutdown()
 def test_temporary_activation_metadata_is_removed_on_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(RuntimeError,'fixture'):
    with activation_message({'method':'activate','description':'x'*2_000_000},tmp) as message:
     self.assertEqual(message['method'],'activateFromFile');self.assertTrue(Path(message['file']).is_file());raise RuntimeError('fixture')
   self.assertFalse(list(Path(tmp).iterdir()))
if __name__=='__main__':unittest.main()
