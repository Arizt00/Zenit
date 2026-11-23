import io,json,tempfile,unittest,zipfile
from pathlib import Path
from backend.server import Application
ROOT=Path(__file__).resolve().parents[1]

class FileSystemErrorContract(unittest.TestCase):
 def test_factories_preserve_code_in_actual_extension_host(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);project=base/'project';project.mkdir();app=Application(ROOT,project,data_dir=base/'profile');app.workspace.trusted=True
   try:
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as bundle:
     bundle.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'filesystem-errors','version':'1.0.0','main':'main.cjs'}))
     bundle.writestr('extension/main.cjs',"const v=require('vscode');exports.activate=()=>v.commands.registerCommand('qa.errors',()=>['FileNotFound','FileExists','FileNotADirectory','FileIsADirectory','NoPermissions','Unavailable'].map(key=>{const e=v.FileSystemError[key](v.Uri.file('/fixture'));return {name:e.name,code:e.code,isError:e instanceof Error,message:e.message};}));")
    store=app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);runtime=app.features.extension_runtime;runtime.start(app.workspace,'qa.filesystem-errors',True)
    result=runtime.request(app.workspace,{'id':'qa.filesystem-errors','method':'command','command':'qa.errors'})['result']
    self.assertEqual([r['code'] for r in result],['FileNotFound','FileExists','FileNotADirectory','FileIsADirectory','NoPermissions','Unavailable']);self.assertTrue(all(r['isError'] and r['name']=='FileSystemError' and 'fixture' in r['message'] for r in result))
   finally:app.features.shutdown();app.runner.shutdown()
if __name__=='__main__':unittest.main()
