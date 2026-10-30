"""Shared help surfaces and persistent snapshots in a disposable real workbench."""
import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright

def main():
 out=ROOT/'qa-output/code-help';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-code-help-') as tmp:
  base=Path(tmp);ws=base/'proyecto';ws.mkdir();source='int main(void) {\n    int value = 42;\n    return value;\n}\n';(ws/'main.c').write_text(source);(ws/'other.py').write_text('print(42)\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'appearance.motion':True});server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},get dock(){return dock},get preview(){return previewUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.c")');page.wait_for_function('__qa.editor.current==="main.c"')
    page.evaluate(r'''window.qaDocs='**value** — signed integer\n\nShort reference.';monaco.languages.registerHoverProvider('c',{provideHover:()=>({contents:[{value:qaDocs}]})});''')
    hover=page.locator('.monaco-hover:visible');diagnostic=page.locator('.zenit-diagnostic-panel:not([hidden])');detail=page.locator('.code-detail-panel');
    def open_hover():
     page.evaluate('__qa.editor.view.focus();__qa.editor.view.setPosition({lineNumber:2,column:9});__qa.editor.view.getAction("editor.action.showHover").run()');hover.wait_for();page.locator('[data-reference-detail]:visible').wait_for();page.wait_for_timeout(250)
    def material(locator):return locator.evaluate('(n)=>{const s=getComputedStyle(n);return {bg:s.backgroundColor,radius:s.borderRadius,opacity:s.opacity,blur:s.backdropFilter}}')
    def open_diagnostic():
     page.wait_for_timeout(80);page.evaluate('__qa.editor.view.focus();__qa.editor.view.setPosition({lineNumber:2,column:9});__qa.editor.view.getAction("zenit.diagnostic.show").run()');diagnostic.wait_for();page.wait_for_timeout(250)
    for theme in ('day','dark','forest'):
     page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)',theme);open_hover();reference=material(hover);page.screenshot(path=str(out/f'{theme}-documentation.png'));page.keyboard.press('Escape')
     page.locator('.editor-tabbar .zenit-tools-menu').click();menu=page.locator('#popover');menu.wait_for(state='visible');page.wait_for_timeout(220);common=material(menu);page.keyboard.press('Escape')
     page.locator('.view-lines').first.click(button='right',position={'x':160,'y':28});context=page.locator('.editor-context-menu:visible').first;context.wait_for();page.wait_for_timeout(220);assert context.locator('.editor-menu-heading').inner_text()=='Acciones del código';assert material(context)==common,(material(context),common);page.get_by_role('menuitem',name='Melody',exact=True).click();child=page.locator('.editor-context-menu:visible').last;assert child.locator('.editor-menu-heading').inner_text()=='Melody';assert child.locator('.editor-menu-heading [data-glyph=sparkles]').count()==1;page.wait_for_timeout(200);page.screenshot(path=str(out/f'{theme}-menus.png'));page.keyboard.press('Escape')
     page.evaluate('__qa.editor.setDiagnostics("main.c",[{startLineNumber:2,startColumn:9,endColumn:14,severity:8,message:"Review this value",source:"Compiler"}],"qa-help")');open_diagnostic();marker=material(diagnostic);assert reference==common==marker,(reference,common,marker);assert '/ 0.65)' in marker['bg'] and marker['opacity']=='1' and marker['radius']=='14px';assert 'blur(24px)' in marker['blur'];page.screenshot(path=str(out/f'{theme}-diagnostic.png'));page.keyboard.press('Escape');page.evaluate('__qa.editor.setDiagnostics("main.c",[],"qa-help")')
    checks.append('Documentation, diagnostics, toolbar menus and nested context menus share 65% surfaces, opaque text, blur and corners in three themes')
    page.evaluate('__qa.platform.savePreference("appearance.theme","day")');open_hover()
    short=hover.bounding_box()['height'];page.keyboard.press('Escape')
    page.evaluate('window.qaDocs="**value** — signed integer\\n\\n"+Array.from({length:60},(_,i)=>"Reference paragraph "+i+" explains the value and its lifetime.\\n\\n").join("")+"```c\\nint value = 42;\\n```"')
    open_hover();long=hover.bounding_box()
    assert long['height']>short+30 and long['height']<=560,{'short':short,'long':long}
    assert page.locator('[data-reference-detail]:visible').is_visible()
    page.screenshot(path=str(out/'long-documentation.png'))
    page.locator('[data-reference-detail]:visible').click();detail.wait_for(state='visible');page.wait_for_timeout(220)
    page.screenshot(path=str(out/'persistent-open.png'))
    (out/'detail-state.json').write_text(json.dumps(detail.evaluate('(n)=>({text:n.innerText,html:n.innerHTML,box:n.getBoundingClientRect().toJSON()})'),indent=2),'utf-8')
    assert 'Reference paragraph 59' in detail.inner_text(),'Missing the end of the provider documentation'
    assert detail.locator('pre').count()>=1,'Missing the formatted code block'
    assert detail.locator('.code-detail-body').evaluate('(n)=>n.scrollHeight>n.clientHeight'),'Long details do not scroll'
    snapshot=detail.locator('.code-detail-body').inner_text()
    page.evaluate('__qa.openFile("other.py")');page.wait_for_function('__qa.editor.current==="other.py"')
    assert detail.locator('.code-detail-body').inner_text()==snapshot
    page.screenshot(path=str(out/'persistent-documentation.png'))
    detail.locator('[data-detail-editor]').click();assert detail.is_visible()
    page.evaluate('__qa.editor.view.focus()');page.keyboard.press('Escape');assert detail.is_visible()
    detail.locator('[data-detail-close]').click();assert detail.is_hidden()
    checks.append('Help grows with content, offers full formatted detail and keeps that snapshot while files and pointer change')
    page.evaluate('__qa.openFile("main.c")');page.wait_for_function('__qa.editor.current==="main.c"');page.evaluate(r'''window.qaMessage='<img src=x onerror=alert(1)> '+Array.from({length:65},(_,i)=>'Diagnostic paragraph '+i+' contains context.').join('\n');__qa.editor.setDiagnostics('main.c',[{startLineNumber:2,startColumn:9,endColumn:14,severity:8,message:qaMessage,source:'Compiler'},{startLineNumber:2,startColumn:9,endColumn:14,severity:4,message:'A second related warning',source:'Analyzer'}],'qa-help');''');open_diagnostic();page.locator('[data-diagnostic-detail]').click();detail.wait_for(state='visible');assert 'Diagnostic paragraph 64' in detail.inner_text() and 'A second related warning' in detail.inner_text();assert detail.locator('img,script,iframe').count()==0;assert '<img src=x onerror=alert(1)>' in detail.inner_text();page.screenshot(path=str(out/'persistent-diagnostic.png'));checks.append('The persistent diagnostic includes complete messages and related markers without interpreting HTML')
    page.evaluate('''()=>{const source=document.createElement('div'),p=document.createElement('p'),script=document.createElement('script'),link=document.createElement('a');p.setAttribute('onclick','window.qaUnsafe=true');p.innerHTML='<strong>Safe formatting</strong>';script.textContent='window.qaUnsafe=true';link.href='javascript:window.qaUnsafe=true';link.textContent='Unsafe link';source.append(p,script,link);document.dispatchEvent(new CustomEvent('zenit:code-detail',{detail:{title:'Provider content',content:[source]}}));}''');assert detail.locator('strong').filter(has_text='Safe formatting').count()==1;assert detail.locator('script,a,[onclick],[href]').count()==0;assert not page.evaluate('window.qaUnsafe===true');checks.append('Provider formatting is copied without scripts, links, event handlers or executable attributes')
    detail.locator('.code-detail-body').focus();page.keyboard.press('Escape');assert detail.is_hidden();page.evaluate('__qa.editor.setDiagnostics("main.c",[],"qa-help")')
    for width,height in ((1024,700),(800,600)):
     page.set_viewport_size({'width':width,'height':height});open_hover();box=hover.bounding_box()
     assert box['x']>=11 and box['y']>=11 and box['x']+box['width']<=width-11 and box['y']+box['height']<=height-11,box
     page.locator('[data-reference-detail]:visible').click();assert detail.is_visible()
     page.screenshot(path=str(out/f'detail-{width}.png'))
     assert page.locator('#editor-mount').bounding_box()['height']>=80,{'editor':page.locator('#editor-mount').bounding_box(),'detail':detail.bounding_box(),'width':width}
     assert page.locator('.code-detail-panel').count()==1
     detail.locator('.code-detail-body').focus();page.keyboard.press('Escape')
    checks.append('Help fits smaller windows; one persistent detail leaves usable editing space and closes with Escape')
    page.set_viewport_size({'width':1600,'height':1000});page.evaluate('document.dispatchEvent(new CustomEvent("zenit:code-detail",{detail:{title:"Guardar",text:"Guardar"}}))')
    page.evaluate('__qa.platform.savePreference("general.locale","en")');page.wait_for_timeout(120)
    assert detail.locator('.code-detail-body').inner_text()=='Guardar' and detail.locator('#code-detail-title').inner_text()=='Guardar'
    detail.locator('[data-detail-close]').click();open_hover()
    assert hover.locator('.code-help-category').inner_text()=='Code documentation'
    assert hover.locator('[data-reference-detail]').inner_text()=='Open details'
    hover.locator('[data-reference-detail]').click();assert detail.locator('.code-detail-heading small').inner_text()=='Code documentation'
    checks.append('UI labels follow the interface language while provider content and symbols remain verbatim')
    assert page.evaluate('__qa.editor.getValue()')==source;assert (ws/'main.c').read_text()==source;assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),'utf-8');print(json.dumps({'passed':len(checks),'checks':checks}),flush=True)
if __name__=='__main__':main()
