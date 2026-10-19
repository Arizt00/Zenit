"""Webview providers remain lazy across the actual Node/Python extension RPC."""
import io,json,tempfile,time,unittest,zipfile
from pathlib import Path
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]
PLUGIN="""const v=require('vscode');let resolved=0,disposed=0,fail=false;
exports.activate=()=>{
 const registration=v.window.registerWebviewViewProvider('qa.sidebar',{async resolveWebviewView(view){resolved++;if(fail){fail=false;throw Error('resolve failed');}view.onDidDispose(()=>disposed++);view.webview.options={enableScripts:true};view.webview.html='<h1>Requested view</h1>';view.webview.onDidReceiveMessage(message=>view.webview.postMessage({answer:message.value+1}));}},{webviewOptions:{retainContextWhenHidden:true}});
 v.commands.registerCommand('qa.state',()=>({resolved,disposed}));
 v.commands.registerCommand('qa.fail',()=>{fail=true;});
 v.commands.registerCommand('qa.unregister',()=>registration.dispose());
 v.commands.registerCommand('qa.background',async()=>{const p=v.window.createWebviewPanel('qa.background','Background',{viewColumn:1,preserveFocus:true});p.webview.html='<p>Background</p>';await p._whenReady();return p._id;});
 v.window.registerTreeDataProvider('qa.tree',{getChildren:()=>[{label:'Actual node'}],getTreeItem:item=>item});
};"""

class WebviewLifecycle(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();base=Path(self.tmp.name);ws=base/'project';ws.mkdir()
  self.app=Application(ROOT,ws,data_dir=base/'profile');self.app.workspace.trusted=True
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as archive:
   archive.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'lazy-webview','version':'1.0.0','main':'main.cjs','contributes':{'views':{'qa':[{'id':'qa.sidebar','name':'Vista solicitada','type':'webview'},{'id':'qa.lazyTree','name':'Árbol pendiente'}]}}}))
   archive.writestr('extension/main.cjs',PLUGIN)
  store=self.app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True)
  self.runtime=self.app.features.extension_runtime;self.activation=self.runtime.start(self.app.workspace,'qa.lazy-webview',True)
 def tearDown(self):
  self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def call(self,command):
  return self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'command','command':command}).get('result')
 def test_activation_preserves_editor_and_focus_resolves_once(self):
  self.assertEqual(self.call('qa.state')['resolved'],0)
  self.assertEqual(self.app.features.extension_services.panels,{})
  self.call('qa.sidebar.focus');self.call('qa.sidebar.focus')
  self.assertEqual(self.call('qa.state')['resolved'],1)
  panels=self.app.features.extension_services.panels;self.assertEqual(len(panels),1)
  panel=next(iter(panels.values()));self.assertEqual(panel['title'],'Vista solicitada');self.assertIn('Requested view',panel['html'])
  self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'webviewMessage','panel':panel['id'],'message':{'value':41}})
  deadline=time.monotonic()+3
  while not panel['messages'] and time.monotonic()<deadline:time.sleep(.01)
  self.assertEqual(panel['messages'][0]['message'],{'answer':42})
 def test_closed_view_can_reopen_and_unregistration_removes_focus(self):
  self.call('qa.sidebar.focus');panel=next(iter(self.app.features.extension_services.panels))
  self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'webviewDispose','panel':panel})
  self.call('qa.sidebar.focus');self.assertEqual(self.call('qa.state'),{'resolved':2,'disposed':1})
  self.call('qa.unregister');self.call('qa.state');self.assertEqual(self.app.features.extension_services.panels,{})
  with self.assertRaises(ValueError):self.call('qa.sidebar.focus')
 def test_failed_resolve_disposes_panel_and_can_retry(self):
  self.call('qa.fail')
  with self.assertRaisesRegex(ValueError,'resolve failed'):self.call('qa.sidebar.focus')
  self.call('qa.state');self.assertEqual(self.app.features.extension_services.panels,{})
  self.call('qa.sidebar.focus');self.assertEqual(self.call('qa.state')['resolved'],2)
 def test_background_panel_preserves_the_requested_focus(self):
  ident=self.call('qa.background');self.assertTrue(self.app.features.extension_services.panels[ident]['preserveFocus'])
 def test_tree_focus_returns_a_real_view_effect_and_host_stays_alive(self):
  result=self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'command','command':'qa.tree.focus'})
  self.assertEqual(result['effects'],[{'treeView':'qa.tree'}]);self.assertEqual(self.call('qa.state')['resolved'],0)
  children=self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'tree','view':'qa.tree'})
  self.assertEqual(children['items'][0]['label'],'Actual node')
 def test_declared_tree_focus_exists_before_conditional_provider(self):
  result=self.runtime.request(self.app.workspace,{'id':'qa.lazy-webview','method':'command','command':'qa.lazyTree.focus'})
  self.assertEqual(result['effects'],[{'treeView':'qa.lazyTree'}])
  host=next(h for h in self.runtime.snapshot()['hosts'] if h['id']=='qa.lazy-webview')
  self.assertFalse(next(v for v in host['views'] if v['id']=='qa.lazyTree')['registered']);self.assertTrue(host['running'])

if __name__=='__main__':unittest.main()
