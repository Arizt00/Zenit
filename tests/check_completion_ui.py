"""Monaco's actual extension adapter, real VSIX host and completion popup."""
import json,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import LumenServer
from tests.test_extension_completions import ExtensionCompletionTests
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/audit-completions';out.mkdir(exist_ok=True);case=ExtensionCompletionTests();case.setUp();app=case.app;f=app.features;errors=[];checks=[]
 f.studio.update({'onboarded':True});f.prefs.update({'general.showWelcome':False,'general.locale':'es','appearance.motion':False,'updates.automatic':False,'files.autoSave':False})
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':950});page.on('pageerror',lambda error:errors.append(str(error)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get preview(){return previewUI},get p(){return platformUI},get editor(){return editor},openFile};')
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.n")')
   page.evaluate('''async()=>{window.__completionProviders=[];const original=monaco.languages.registerCompletionItemProvider;monaco.languages.registerCompletionItemProvider=(language,provider)=>{if(language==='nc')__completionProviders.push(provider);return original(language,provider);};__qa.preview.registerExtensions((await __qa.p.api('/extensions/runtime')).hosts,{force:true});__qa.editor.models.get('main.n').model.setValue('ren');}''')
   assert page.evaluate('__completionProviders.length')==1;checks.append('Two extension providers share one real Monaco adapter without duplicated lists')
   result=page.evaluate('''async()=>{const model=__qa.editor.models.get('main.n').model;window.__completionList=await __completionProviders[0].provideCompletionItems(model,new monaco.Position(1,4),{triggerKind:2,triggerCharacter:'.'},{});return {incomplete:__completionList.incomplete,kind:__completionList.suggestions[0].kind,expected:monaco.languages.CompletionItemKind.Function,detail:__completionList.suggestions[0].detail};}''')
   assert result['incomplete'] and result['kind']==result['expected'] and result['detail']=='trigger=2;character=.';checks.append('Incomplete state, context, function icon and snippet survive backend-to-Monaco transport')
   result=page.evaluate('''async()=>{window.__resolved=await __completionProviders[0].resolveCompletionItem(__completionList.suggestions[0],{});return __resolved;}''')
   assert result['documentation']['value']=='Native nC function' and result['documentation']['isTrusted'] is False and result['additionalTextEdits'][0]['text']=='// import\n';checks.append('Lazy resolution retrieves real extension documentation and additional edits safely')
   page.evaluate('__qa.editor.view.focus();__qa.editor.view.setPosition({lineNumber:1,column:4});__qa.editor.view.getAction("editor.action.triggerSuggest").run()');expect(page.locator('.suggest-widget.visible')).to_contain_text('renderFloat',timeout=15000);page.screenshot(path=str(out/'suggestions.png'));checks.append('The actual editor popup displays the extension suggestion')
   assert page.evaluate('''async()=>{const original=__completionList.suggestions[0];__qa.editor.models.get('main.n').model.setValue('changed');return (await __completionProviders[0].resolveCompletionItem(original,{}))===original;}''');checks.append('Stale completion details are discarded after the document changes')
   assert not errors,errors;browser.close()
 finally:server.shutdown();server.server_close();case.tearDown()
 (out/'verification.json').write_text(json.dumps({'passed':True,'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)
if __name__=='__main__':main()
