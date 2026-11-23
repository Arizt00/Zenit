"""Real VSIX/RPC completion behavior, including failure isolation and lazy details."""
import io,json,tempfile,unittest,zipfile
from pathlib import Path
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=r'''
const v=require('vscode');
exports.activate=()=>{
 v.languages.registerCompletionItemProvider('nc',{
  provideCompletionItems(doc,pos,token,context){
   if(doc.getText()==='explode')throw Error('Deliberately failed provider');
   const item=new v.CompletionItem('renderFloat',v.CompletionItemKind.Function);
   item.detail='trigger='+context.triggerKind+';character='+context.triggerCharacter;
   item.insertText=new v.SnippetString('renderFloat(${1:value}, 2)');item._private={identity:42};
   return new v.CompletionList([item],true);
  },
  resolveCompletionItem(item){if(item._private.identity!==42)throw Error('Original item identity lost');item.documentation=new v.MarkdownString('Native nC function');item.additionalTextEdits=[v.TextEdit.insert(new v.Position(0,0),'// import\n')];return item;}
 },'.');
 v.languages.registerCompletionItemProvider('nc',{provideCompletionItems(){return [new v.CompletionItem('fallback',v.CompletionItemKind.Variable)];}});
};
'''

class ExtensionCompletionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);root=Path(self.temp.name);project=root/'project';project.mkdir();(project/'main.n').write_text('value')
  self.app=Application(ROOT,project,data_dir=root/'profile');self.ws=self.app.workspace;self.ws.trusted=True;self.runtime=self.app.features.extension_runtime;raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as archive:
   archive.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'completions','version':'1.0.0','main':'main.cjs'}));archive.writestr('extension/main.cjs',PLUGIN)
  store=self.app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);self.runtime.start(self.ws,'qa.completions',True)
 def tearDown(self):self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def call(self,**body):return self.runtime.request(self.ws,{'id':'qa.completions','document':{'path':'main.n','text':'value','language':'nc'},**body})
 def test_incomplete_list_and_trigger_context_survive_rpc(self):
  result=self.call(method='provide',kind='completion',position={'line':0,'character':5},context={'triggerKind':2,'triggerCharacter':'.'})
  self.assertTrue(result['incomplete']);self.assertEqual(result['items'][0]['detail'],'trigger=2;character=.');self.assertEqual(result['items'][0]['insertText']['value'],'renderFloat(${1:value}, 2)')
 def test_resolver_receives_original_item_and_fills_documentation(self):
  item=self.call(method='provide',kind='completion',position={'line':0,'character':5})['items'][0]
  result=self.call(method='resolveCompletion',completion=item['_lumenCompletion'])['item'];self.assertEqual(result['documentation']['value'],'Native nC function');self.assertEqual(result['additionalTextEdits'][0]['newText'],'// import\n')
 def test_failed_provider_does_not_discard_another_provider_result(self):
  result=self.call(method='provide',kind='completion',document={'path':'main.n','text':'explode','language':'nc'},position={'line':0,'character':7})
  self.assertEqual([x['label'] for x in result['items']],['fallback']);self.assertTrue(result['providerErrors']);self.assertIn('Deliberately failed provider',result['providerErrors'][0]['message'])
 def test_resolving_an_item_after_source_changes_is_rejected(self):
  item=self.call(method='provide',kind='completion',position={'line':0,'character':5})['items'][0]
  with self.assertRaisesRegex(ValueError,'cambió|caducó'):
   self.call(method='resolveCompletion',completion=item['_lumenCompletion'],document={'path':'main.n','text':'changed','language':'nc'})

if __name__=='__main__':unittest.main()
