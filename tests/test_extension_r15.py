import io,json,tempfile,unittest,zipfile,time
from pathlib import Path
from unittest.mock import patch
from backend.server import Application
ROOT=Path(__file__).resolve().parents[1]
PLUGIN="""const v=require('vscode');let type;exports.activate=context=>{
v.commands.registerCommand('qa.uri',()=>({relative:v.Uri.parse('relative/path').path,empty:v.Uri.parse('').toString(),joined:v.Uri.joinPath(v.Uri.file(context.extensionPath),'a b').path,timeline:new v.TimelineItem('Now',42),fresh:v.env.isNewAppInstall}));
v.commands.registerCommand('qa.decorate',()=>{type=v.window.createTextEditorDecorationType({color:'#ff0000',isWholeLine:true});v.window.activeTextEditor.setDecorations(type,[new v.Range(0,0,0,3)]);return type.key;});
v.commands.registerCommand('qa.dispose',()=>type.dispose());
v.commands.registerCommand('qa.secrets',async()=>{await context.secrets.store('qa','test only 123');const read=await context.secrets.get('qa');await context.secrets.delete('qa');return [read,await context.secrets.get('qa')];});
let checked=0;const leaf={label:'Hoja',checkboxState:v.TreeItemCheckboxState.Unchecked};const tree=v.window.createTreeView('qa.check',{treeDataProvider:{getChildren:()=>[leaf],getTreeItem:x=>x}});tree.onDidChangeCheckboxState(e=>{leaf.checkboxState=e.items[0][1];checked=leaf.checkboxState;});v.commands.registerCommand('qa.checked',()=>checked);
v.workspace.registerEditSessionIdentityProvider('file',{provideEditSessionIdentity:folder=>'qa:'+folder.name,provideEditSessionIdentityMatch:(a,b)=>a===b?v.EditSessionIdentityMatch.Complete:v.EditSessionIdentityMatch.None});
v.window.registerTerminalLinkProvider({provideTerminalLinks:ctx=>ctx.line.includes('LINK')?[{startIndex:ctx.line.indexOf('LINK'),length:4,terminal:ctx.terminal}]:[],handleTerminalLink:link=>link.terminal.sendText('print(42)')});
v.commands.registerCommand('qa.tabs',()=>v.window.tabGroups.all.flatMap(g=>g.tabs.map(t=>({label:t.label,dirty:t.isDirty,active:t.isActive,text:t.input instanceof v.TabInputText}))));
v.window.registerUriHandler({handleUri:uri=>context.globalState.update('uri',uri.toString())});v.commands.registerCommand('qa.lastUri',()=>context.globalState.get('uri'));
};"""
class ExtensionR15(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();base=Path(self.tmp.name);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('one = 1\n');self.app=Application(ROOT,ws,data_dir=base/'profile');self.app.workspace.trusted=True
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('extension/package.json',json.dumps({'name':'r15','publisher':'qa','version':'1.0.0','main':'main.cjs'}));z.writestr('extension/main.cjs',PLUGIN)
  store=self.app.features.extensions;store.install(store.inspect_bytes(data.getvalue())['ticket'],True);self.runtime=self.app.features.extension_runtime;self.runtime.start(self.app.workspace,'qa.r15',True)
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def command(self,name):return self.runtime.request(self.app.workspace,{'id':'qa.r15','method':'command','command':'qa.'+name,'document':{'path':'main.py','text':'one = 1\n','language':'python'}}).get('result')
 def test_real_uri_encoding_new_install_and_timeline_item(self):
  r=self.command('uri');self.assertEqual(r['relative'],'/relative/path');self.assertEqual(r['empty'],'file:///');self.assertIn('a b',r['joined']);self.assertEqual(r['timeline']['timestamp'],42);self.assertTrue(r['fresh'])
 def test_decorations_cross_real_node_python_service_and_dispose(self):
  key=self.command('decorate');deadline=time.monotonic()+2
  while not self.app.features.extension_services.snapshot()['editorDecorations'] and time.monotonic()<deadline:time.sleep(.02)
  items=self.app.features.extension_services.snapshot()['editorDecorations'];self.assertEqual(items[0]['key'],key);self.assertEqual(items[0]['path'],'main.py');self.assertEqual(items[0]['ranges'][0]['end']['character'],3)
  self.command('dispose')
  while self.app.features.extension_services.snapshot()['editorDecorations'] and time.monotonic()<deadline:time.sleep(.02)
  self.assertEqual(self.app.features.extension_services.snapshot()['editorDecorations'],[])
 def test_secure_storage_is_scoped_and_never_written_to_configuration(self):
  class Native:
   data={}
   def get_password(self,s,k):return self.data.get((s,k))
   def set_password(self,s,k,v):self.data[s,k]=v
   def delete_password(self,s,k):self.data.pop((s,k),None)
  with patch('backend.providers.CredentialVault._native',return_value=Native()):self.assertEqual(self.command('secrets'),['test only 123',None])
  for p in Path(self.tmp.name).rglob('*.json'):self.assertNotIn('test only 123',p.read_text(encoding='utf-8'))
 def test_uri_handler_receives_authenticated_dispatch(self):
  self.app.features.post('/extensions/uri',{'uri':'lumen://qa.r15/open?line=3'});deadline=time.monotonic()+2
  while time.monotonic()<deadline:
   if self.command('lastUri'):break
   time.sleep(.02)
  from urllib.parse import unquote
  self.assertEqual(unquote(self.command('lastUri')),'lumen://qa.r15/open?line=3')

 def test_identity_and_real_tree_checkbox_dispatch(self):
  def request(**body):return self.runtime.request(self.app.workspace,{'id':'qa.r15',**body})
  tree=request(method='tree',view='qa.check');self.assertEqual(tree['items'][0]['checkboxState'],0)
  request(method='treeCheckbox',view='qa.check',element=tree['items'][0]['key'],checkboxState=1)
  self.assertEqual(self.command('checked'),1);self.assertEqual(request(method='tree',view='qa.check')['items'][0]['checkboxState'],1)
  self.assertEqual(request(method='editSessionIdentity',scheme='file'),'qa:project')
  self.assertEqual(request(method='editSessionIdentity',scheme='file',action='match',identity1='a',identity2='a'),100)
 def test_tabs_follow_actual_browser_snapshot(self):
  service=self.app.features.extension_services
  service.editor_state(self.app.workspace,{'owner':'browser1','editors':[],'tabs':[{'path':'main.py','dirty':True,'active':True}]})
  self.assertEqual(self.command('tabs'),[{'label':'main.py','dirty':True,'active':True,'text':True}])
 def test_terminal_provider_activates_against_real_pty(self):
  from backend.terminals import TerminalSession
  import sys
  session=TerminalSession({'id':'qa','label':'QA','argv':[sys.executable,'-u','-i'],'kind':'qa'},self.app.workspace.root,ROOT,100,26)
  self.app.features.terminals.sessions[session.id]=session
  result=self.runtime.request(self.app.workspace,{'id':'qa.r15','method':'terminalLinks','line':'go LINK','terminal':session.id})
  self.assertEqual(result['items'][0]['startIndex'],3)
  self.runtime.request(self.app.workspace,{'id':'qa.r15','method':'terminalLink','link':result['items'][0]['id']})
  deadline=time.monotonic()+8
  while '42' not in session.read()['data'] and time.monotonic()<deadline:time.sleep(.03)
  self.assertIn('42',session.read()['data'])

if __name__=='__main__':unittest.main()
