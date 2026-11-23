"""Real provider tokens and queued requests in an isolated VSIX host."""
import io,json,tempfile,threading,time,unittest,zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.server import Application

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=r'''
const v=require('vscode');let calls=[],cancelled=[],resolutions=0;
function slow(doc,token){calls.push(doc.getText());console.log('START:'+doc.getText());
 return new Promise(resolve=>{const timer=setTimeout(()=>resolve({contents:['late']}),8000);
 token.onCancellationRequested(()=>{clearTimeout(timer);cancelled.push(doc.getText());resolve({contents:['cancelled']});});});}
exports.activate=()=>{
 v.languages.registerHoverProvider('nc',{provideHover(doc,pos,token){return doc.getText().startsWith('slow')?slow(doc,token):{contents:[doc.getText()]};}});
 v.languages.registerCompletionItemProvider('nc',{
  provideCompletionItems(){return [new v.CompletionItem('answer',v.CompletionItemKind.Function)];},
  async resolveCompletionItem(item,token){resolutions++;if(resolutions===1){console.log('RESOLVE_STARTED');await new Promise(resolve=>{const timer=setTimeout(resolve,8000);token.onCancellationRequested(()=>{clearTimeout(timer);resolve();});});}item.detail='resolved:'+resolutions;return item;}
 });
 v.commands.registerCommand('qa.state',()=>({calls,cancelled,resolutions,document:v.window.activeTextEditor?.document.getText()}));
};
'''

class ExtensionCancellationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);base=Path(self.temp.name);project=base/'project';project.mkdir();(project/'main.n').write_text('value')
  self.app=Application(ROOT,project,data_dir=base/'profile');self.ws=self.app.workspace;self.ws.trusted=True;self.runtime=self.app.features.extension_runtime;raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'cancellation','version':'1.0.0','main':'main.cjs'}));z.writestr('extension/main.cjs',PLUGIN)
  store=self.app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);self.runtime.start(self.ws,'qa.cancellation',True);self.host=self.runtime.hosts['qa.cancellation'];self.pool=ThreadPoolExecutor(max_workers=3)
 def tearDown(self):self.pool.shutdown();self.app.features.shutdown();self.app.runner.shutdown();self.temp.cleanup()
 def call(self,text='value',**extra):return self.runtime.request(self.ws,{'id':'qa.cancellation','method':'provide','kind':'hover','position':{'line':0,'character':1},'document':{'path':'main.n','text':text,'language':'nc'},**extra})
 def cancel(self,key):return self.runtime.cancel(self.ws,{'id':'qa.cancellation','requestKey':key})
 def wait_log(self,text):
  deadline=time.monotonic()+5
  while text not in self.host.logs and time.monotonic()<deadline:time.sleep(.01)
  self.assertIn(text,self.host.logs)
 def state(self):return self.runtime.request(self.ws,{'id':'qa.cancellation','method':'command','command':'qa.state'})['result']
 def test_running_provider_receives_token_and_next_document_works_without_restart(self):
  pid=self.host.process.pid;key='running-provider-123';task=self.pool.submit(self.call,'slow first',requestKey=key);self.wait_log('START:slow first');self.cancel(key)
  self.assertTrue(task.result(timeout=3)['cancelled']);self.assertEqual(self.call('next')['items'][0]['contents'],['next']);state=self.state()
  self.assertEqual(state['cancelled'],['slow first']);self.assertEqual(state['document'],'next');self.assertEqual(self.host.process.pid,pid);self.assertFalse(self.host.capabilities.get('providerErrors'))
 def test_queued_cancel_skips_provider_and_does_not_replace_the_active_snapshot(self):
  first=self.pool.submit(self.call,'slow first',requestKey='first-operation-123');self.wait_log('START:slow first')
  second=self.pool.submit(self.call,'slow queued',requestKey='queued-operation-123')
  deadline=time.monotonic()+3
  while len(self.host.provider_operations.active)<2 and time.monotonic()<deadline:time.sleep(.01)
  self.cancel('queued-operation-123');self.cancel('first-operation-123')
  self.assertTrue(first.result(timeout=3)['cancelled']);self.assertTrue(second.result(timeout=3)['cancelled']);state=self.state()
  self.assertEqual(state['calls'],['slow first']);self.assertEqual(state['document'],'slow first')
 def test_cancel_before_request_is_remembered_without_poisoning_the_next_query(self):
  key='pre-cancelled-123';self.cancel(key);self.assertTrue(self.call('slow skipped',requestKey=key)['cancelled']);self.assertEqual(self.state()['calls'],[])
  self.assertEqual(self.call('normal',requestKey='normal-operation-123')['items'][0]['contents'],['normal'])
 def test_cancelled_completion_resolution_can_be_retried(self):
  item=self.call(kind='completion')['items'][0];key='resolve-operation-123'
  task=self.pool.submit(self.call,method='resolveCompletion',completion=item['_lumenCompletion'],requestKey=key);self.wait_log('RESOLVE_STARTED');self.cancel(key)
  self.assertTrue(task.result(timeout=3)['cancelled']);result=self.call(method='resolveCompletion',completion=item['_lumenCompletion']);self.assertEqual(result['item']['detail'],'resolved:2')
 def test_early_cancellation_memory_is_bounded_and_ids_are_validated(self):
  for n in range(300):self.cancel('early-cancellation-'+str(n))
  self.assertLessEqual(len(self.host.provider_operations.early),256)
  with self.assertRaises(ValueError):self.cancel('../bad')

if __name__=='__main__':unittest.main()
