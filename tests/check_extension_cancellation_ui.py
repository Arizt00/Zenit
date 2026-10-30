"""A real Monaco hover cancels through HTTP, Python and the VSIX token."""
import json,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import LumenServer
from tests.test_extension_cancellation import ExtensionCancellationTests
from playwright.sync_api import sync_playwright

def main():
 out=ROOT/'qa-output/provider-cancellation-ui';out.mkdir(exist_ok=True);case=ExtensionCancellationTests();case.setUp();app=case.app;f=app.features;errors=[];checks=[]
 f.studio.update({'onboarded':True});f.prefs.update({'general.showWelcome':False,'general.locale':'es','editor.autoLanguageServer':False,'updates.automatic':False,'files.autoSave':False})
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get ed(){return editor},get p(){return platformUI},get preview(){return previewUI},openFile};')
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('__qa.openFile("main.n")');page.wait_for_function('__qa.ed.current==="main.n"')
   page.evaluate('''async()=>{const original=monaco.languages.registerHoverProvider;monaco.languages.registerHoverProvider=(language,p)=>{if(language==='nc')window.__hover=p;return original(language,p);};__qa.preview.registerExtensions((await __qa.p.api('/extensions/runtime')).hosts,{force:true});const model=__qa.ed.view.getModel();model.setValue('slow original');window.__pendingHover=__hover.provideHover(model,new monaco.Position(1,2),{isCancellationRequested:false});}''')
   case.wait_log('START:slow original');pid=case.host.process.pid
   page.evaluate('__qa.ed.view.getModel().setValue("new source")');assert page.evaluate('async()=>await __pendingHover') is None
   state=case.state();assert state['cancelled']==['slow original'];assert case.host.process.pid==pid;checks.append('Typing cancels the real running VSIX provider from Monaco through HTTP and returns no stale hover')
   assert page.evaluate('async()=>await __hover.provideHover(__qa.ed.view.getModel(),new monaco.Position(1,2),{})')['contents'][0]['value']=='new source';checks.append('The next source gets its own hover without restarting the extension process')
   page.evaluate('''()=>{__qa.ed.view.getModel().setValue('slow token');window.__listeners=new Set();const token={isCancellationRequested:false,onCancellationRequested(fn){__listeners.add(fn);return {dispose:()=>__listeners.delete(fn)};}};window.__pendingHover=__hover.provideHover(__qa.ed.view.getModel(),new monaco.Position(1,2),token);}''');case.wait_log('START:slow token');page.evaluate('for(const fn of [...__listeners])fn()');assert page.evaluate('async()=>await __pendingHover') is None;assert case.state()['cancelled']==['slow original','slow token'];checks.append('A Monaco cancellation token also stops the provider without changing the file')
   assert not errors,errors;browser.close()
 finally:server.shutdown();server.server_close();case.tearDown()
 (out/'report.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)

if __name__=='__main__':main()
