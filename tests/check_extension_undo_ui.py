"""Real extension edits must remain undoable across buffer polling and windows."""
import argparse,io,json,sys,tempfile,threading,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

PLUGIN=r'''
const v=require('vscode');
exports.activate=()=>v.commands.registerCommand('qa.replace',async(name,text,create=false)=>{
 const uri=v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,name),edit=new v.WorkspaceEdit();
 if(create)edit.createFile(uri);
 const document=await v.workspace.openTextDocument(uri).catch(()=>null);
 edit.replace(uri,document?new v.Range(new v.Position(0,0),document.positionAt(document.getText().length)):new v.Range(0,0,0,0),text);
 return v.workspace.applyEdit(edit);
});
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 checks=[];errors=[]
 def passed(text):checks.append(text);print('PASS',text,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-extension-undo-',ignore_cleanup_errors=True) as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'lf.py').write_bytes(b'print("disk")\n');(ws/'crlf.py').write_bytes(b'print("disk")\r\n')
  app=Application(args.root,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'files.autoSave':False})
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'undo','version':'1.0.0','main':'main.cjs'}));z.writestr('extension/main.cjs',PLUGIN)
  store=app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);runtime=app.features.extension_runtime;runtime.start(app.workspace,'qa.undo',True)
  services=app.features.extension_services;emit=services.emit;edits=[]
  def track(command,**data):
   if command=='zenit.workspace.edit':edits.append(data['edit'])
   return emit(command,**data)
  services.emit=track
  def replace(path,text,create=False):
   result=runtime.request(app.workspace,{'id':'qa.undo','method':'command','command':'qa.replace','arguments':[path,text,create]})['result'];assert result
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);page.wait_for_function('window.lumen?.ready')
    def text_is(view,path,text):view.wait_for_function(r'([path,text])=>monaco.editor.getModels().find(m=>m.uri.path.endsWith("/"+path))?.getValue().replace(/\r\n?/g,"\n")===text',arg=[path,text])
    def stable(view,path,text):
     text_is(view,path,text);view.wait_for_timeout(1000);text_is(view,path,text)
    def key(view,key):view.locator('.monaco-editor textarea').first.focus();view.keyboard.press(key)
    replace('created.py','print("extension ñ")\n',True);page.locator('[data-file="created.py"]').click();text_is(page,'created.py','print("extension ñ")\n')
    key(page,'Control+z');stable(page,'created.py','');assert (ws/'created.py').read_bytes()==b''
    assert app.features.buffers.items['created.py']['text']==''
    passed('Ctrl+Z on an extension-created file survives repeated buffer polling and publishes the undone text without saving the source')
    emit('zenit.workspace.edit',edit=edits[-1]);stable(page,'created.py','')
    passed('A delayed duplicate extension event cannot restore text after the user has undone it')
    key(page,'Control+y');stable(page,'created.py','print("extension ñ")\n');assert 'extension ñ' in app.features.buffers.items['created.py']['text'];assert (ws/'created.py').read_bytes()==b''
    passed('Ctrl+Y restores the extension edit once and keeps it unsaved')
    for path,original in [('lf.py',b'print("disk")\n'),('crlf.py',b'print("disk")\r\n')]:
     page.locator('[data-file="'+path+'"]').click();text_is(page,path,'print("disk")\n');replace(path,'print("changed ñ")\n');stable(page,path,'print("changed ñ")\n')
     key(page,'Control+z');stable(page,path,'print("disk")\n');key(page,'Control+y');stable(page,path,'print("changed ñ")\n');assert (ws/path).read_bytes()==original
    passed('Existing LF and CRLF files undo and redo extension edits without empty undo steps or disk changes')
    key(page,'Control+End');page.keyboard.type('local');stable(page,'crlf.py','print("changed ñ")\nlocal');replace('crlf.py','print("formatted")\n');stable(page,'crlf.py','print("formatted")\n')
    key(page,'Control+z');stable(page,'crlf.py','print("changed ñ")\nlocal');key(page,'Control+z');stable(page,'crlf.py','print("changed ñ")\n')
    assert (ws/'crlf.py').read_bytes()==b'print("disk")\r\n'
    passed('Undo preserves prior unsaved typing as a separate step before an extension transformation')
    page.locator('[data-file="created.py"]').click();child=context.new_page();child.on('pageerror',lambda e:errors.append(str(e)));child.goto(url+'?panel=editor&file=created.py');child.wait_for_function('window.lumen?.ready');stable(child,'created.py','print("extension ñ")\n')
    replace('created.py','print("both windows")\n');stable(page,'created.py','print("both windows")\n');stable(child,'created.py','print("both windows")\n')
    key(page,'Control+z');stable(page,'created.py','print("extension ñ")\n');stable(child,'created.py','print("extension ñ")\n')
    key(page,'Control+y');stable(page,'created.py','print("both windows")\n');stable(child,'created.py','print("both windows")\n')
    passed('A detached editor receives undo and redo from the main window without reapplying the extension edit')
    child.close();page.screenshot(path=str(args.output/'extension-undo.png'));assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 report={'checks':checks,'errors':errors,'frozen':bool(getattr(sys,'frozen',False))};(args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
