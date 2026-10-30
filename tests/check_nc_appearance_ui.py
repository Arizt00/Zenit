"""Real installed nC grammar, semantic provider, file icons and bracket editing."""
import hashlib,io,json,sys,tempfile,threading,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

out=ROOT/'qa-output/nc-appearance';out.mkdir(exist_ok=True);checks=[];errors=[];details={}
package=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'web/assets/extensions/nc-language-1.0.0-21v.zenit.4.vsix'
with tempfile.TemporaryDirectory(prefix='znc-',dir=Path.home()/'AppData/Local/Temp') as temp:
 root=Path(temp);ws=root/'project';ws.mkdir()
 files={'vistaActual.n':'nc','machine_mode.nm':'nc-machine','root_mode.nb':'nc-root','primitive_mode.nbb':'nc-primitive','primitive_mode.ncp':'nc-hardware'}
 with zipfile.ZipFile(package) as archive:
  for file in files:(ws/file).write_bytes(archive.read('extension/test-fixtures/'+('high_level.n' if file=='vistaActual.n' else file)))
  provenance=json.loads(archive.read('extension/JETBRAINS-PROVENANCE.json'))
 (ws/'object.nbo').write_text('; Backend object\n.section .text\n    entry section=.text offset=0 size=16 visibility=global\n',encoding='utf-8');files['object.nbo']='nc-backend-object'
 (ws/'target.init').write_text('NCI1\nschema:1\ntarget:x86_64\npointer-width:64\nendian:little\n',encoding='utf-8');files['target.init']='nc-target-init'
 (ws/'brackets.n').write_text('main :: in {\n    print([1, 2]); // (ignored)\n    "[string]";\n}\n',encoding='utf-8')
 (ws/'broken.n').write_text((ws/'vistaActual.n').read_text('utf-8').replace('vistaActual {','vistaRota {').replace('valor >> int <- 42;', 'valor >> int <- ;'),encoding='utf-8')
 (ws/'binary.nbo').write_bytes(b'\x7fELF\x00\x01')
 app=Application(ROOT,ws,data_dir=root/'profile');app.workspace.trusted=True;f=app.features
 review=f.extensions.inspect_file(package);f.extensions.install(review['ticket'],True)
 # Languages associated only with filenames must be registered before applying
 # their configuration; otherwise one extension blocks every later contribution.
 fixture=io.BytesIO()
 with zipfile.ZipFile(fixture,'w') as z:
  z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'filename-language','version':'1.0.0','license':'MIT','contributes':{'languages':[{'id':'qa-workflow','filenames':['workflow.yml'],'configuration':'config.json'}]}}))
  z.writestr('extension/config.json',json.dumps({'comments':{'lineComment':'#'}}))
 review=f.extensions.inspect_bytes(fixture.getvalue());f.extensions.install(review['ticket'],True)
 f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'editor.bracketColors':True,'editor.formatOnType':False,'appearance.iconTheme':'zenit','security.confirmRoutineActions':False});f.studio.update({'onboarded':True});f.extension_runtime.start(app.workspace,'nc-lang.nc-language',True)
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get preview(){return previewUI},get editor(){return editor},openFile};')
   def delayed_contributions(route):
    response=route.fetch()
    page.evaluate('__qa.openFile("vistaActual.n")')
    details['startupTabIcon']=page.locator('[data-tab="vistaActual.n"] img').get_attribute('src')
    assert details['startupTabIcon']=='/assets/languages/nc.png'
    route.fulfill(response=response)
   page.route('**/api/platform/extensions/contributions',delayed_contributions)
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.wait_for_function('__qa.editor?.textmate?.loaded.length===7')
   assert not page.evaluate('__qa.platform.extensionContributions.errors'),page.evaluate('__qa.platform.extensionContributions.errors')
   assert page.evaluate('monaco.languages.getLanguages().some(l=>l.id==="qa-workflow")')
   checks.append('A filename-only contributed language no longer interrupts grammar, theme or icon loading')
   icons={}
   for file,language in files.items():
    page.locator(f'[data-file="{file}"]').click();page.wait_for_function('(id)=>__qa.editor.view.getModel()?.getLanguageId()===id',arg=language)
    if not file.endswith('.init'):
     import base64
     icon=page.locator(f'[data-file="{file}"] .file-type img').get_attribute('src');assert icon and icon.startswith('data:image/svg+xml;base64,');icons[file]=icon
     assert hashlib.sha256(base64.b64decode(icon.split(',',1)[1])).hexdigest()==provenance['iconSha256'][file.split('.')[-1]]
     assert page.locator(f'[data-tab="{file}"] .file-type img').get_attribute('src')==icon
     assert page.locator('#breadcrumbs .file-type img').get_attribute('src')==icon
    tokens=page.evaluate('()=>{const model=__qa.editor.view.getModel();model.tokenization.forceTokenization(model.getLineCount());return Array.from({length:model.getLineCount()},(_,n)=>{const t=model.tokenization.getLineTokens(n+1);return Array.from({length:t.getCount()},(_,i)=>({start:t.getStartOffset(i),color:t.getForeground(i),metadata:t.getMetadata(i)}))})}')
    assert len({t['color'] for line in tokens for t in line})>1,(file,tokens)
    if language=='nc-machine':
     page.wait_for_function('()=>[...document.querySelectorAll(".view-line span span")].some(s=>s.textContent==="mov"&&getComputedStyle(s).color==="rgb(243, 114, 44)")')
     page.mouse.move(1400,20);page.screenshot(path=str(out/'nc-machine-jetbrains.png'))
   assert len(set(icons.values()))==6;checks.append('Seven nC language modes keep their grammars; six file icons match the user-selected JetBrains JAR byte for byte')
   assert app.workspace.open_file('binary.nbo')['kind']=='binary';checks.append('Textual .nbo uses the IR grammar; actual binary bytes still open in the hexadecimal editor')
   page.locator('[data-file="brackets.n"]').click();page.wait_for_function('__qa.editor.view.getModel()?.getLanguageId()==="nc"')
   page.wait_for_function('document.querySelectorAll(".bracket-highlighting-0,.bracket-highlighting-1,.bracket-highlighting-2").length>=6')
   colors=page.evaluate('()=>[...new Set([...document.querySelectorAll("[class*=bracket-highlighting-]")].map(e=>getComputedStyle(e).color))]');assert len(colors)>=3,colors;details['bracketColors']=colors
   checks.append('Nested braces, square brackets and parentheses are matched and receive three visible colours')
   page.evaluate('()=>{const e=__qa.editor;e.view.getModel().setValue("");e.view.focus();e.view.setPosition({lineNumber:1,column:1})}');page.keyboard.type('{');assert page.evaluate('__qa.editor.getValue()')=='{}'
   page.keyboard.press('Enter');text=page.evaluate('__qa.editor.getValue()').replace('\r\n','\n');assert text.startswith('{\n    \n}'),repr(text)
   page.evaluate('()=>{const e=__qa.editor;e.view.getModel().setValue("main :: in {} ");e.view.setPosition({lineNumber:1,column:13});e.view.focus()}');page.keyboard.press('Control+/');assert page.evaluate('__qa.editor.getValue()').startswith('//')
   checks.append('Typing closes brace pairs; Enter indents inside the pair; Ctrl+/ applies the package comment syntax')
   page.locator('[data-file="vistaActual.n"]').click();page.wait_for_function('__qa.editor.semanticStyles.classifications.length>0',timeout=20000)
   assert 'use::stoud::' not in page.evaluate('__qa.editor.getValue()') and ' <- ' in page.evaluate('__qa.editor.getValue()')
   themes=page.evaluate('__qa.platform.extensionThemes.map(t=>({id:t.id,label:t.label,uiTheme:t.uiTheme}))');details['themes']=themes
   for mode in ['vs-dark','vs']:
    selected=next((t for t in themes if t['uiTheme']==mode),None);assert selected,themes
    page.evaluate('async(id)=>__qa.platform.savePreference("appearance.extensionTheme",id)',selected['id']);page.wait_for_timeout(400)
    rules=page.evaluate('__qa.editor.semanticStyles.rules');assert len({r.get('foreground') for r in rules})>2,rules
    expected='#0284c7' if mode=='vs' else '#22d3ee'
    assert page.evaluate('__qa.editor.semanticStyles.resolve("printFunction",[],"nc").foreground')==expected
    page.wait_for_function('(expected)=>{const color="rgb("+[1,3,5].map(n=>parseInt(expected.slice(n,n+2),16)).join(", ")+")";return [...document.querySelectorAll(".view-line span span")].some(s=>s.textContent==="println"&&getComputedStyle(s).color===color)}',arg=expected,timeout=15000)
    details[mode]={'semanticCategories':page.evaluate('__qa.editor.semanticStyles.classifications'),'colours':sorted(set(r.get('foreground','') for r in rules))}
    page.mouse.move(1100,600)
    page.screenshot(path=str(out/f'nc-{mode}.png'))
   checks.append('Current compact syntax and rendered semantic colours use the exact light/dark pairs exported from the distributed JetBrains attribute class')
   page.locator('[data-file="broken.n"]').click()
   page.wait_for_function('()=>monaco.editor.getModelMarkers({resource:__qa.editor.view.getModel().uri}).some(m=>m.severity>=8)',timeout=20000)
   broken=page.evaluate('monaco.editor.getModelMarkers({resource:__qa.editor.view.getModel().uri}).map(m=>({message:m.message,severity:m.severity}))')
   assert any('Invalid expression' in m['message'] for m in broken),broken
   assert not any('routing failure' in m['message'] for m in broken),broken
   details['compilerError']=broken
   page.locator('[data-file="vistaActual.n"]').click();page.wait_for_timeout(2000)
   details['sourceDiagnostics']=page.evaluate('monaco.editor.getModelMarkers({resource:__qa.editor.view.getModel().uri}).map(m=>({message:m.message,source:m.source,owner:m.owner,severity:m.severity,line:m.startLineNumber}))')
   assert not [m for m in details['sourceDiagnostics'] if m['severity']>=8],details['sourceDiagnostics']
   checks.append('The valid modern nC fixture has no false routing error or native-to-WSL compiler fallback')
   original=page.evaluate('__qa.editor.getValue()');point=next({'lineNumber':i+1,'column':line.index('valor')+2} for i,line in enumerate(original.splitlines()) if 'valor >>' in line);page.evaluate('__qa.editor.split("vistaActual.n")')
   page.evaluate('(point)=>{__qa.editor.view.setPosition(point);__qa.editor.view.focus();void __qa.editor.view.getAction("editor.action.rename").run();}',point)
   rename=page.locator('.rename-box input');expect(rename).to_be_focused();rename.fill('valorRevisado');rename.press('Enter');expect(page.locator('.editor-change-review')).to_be_visible(timeout=20000);expect(page.locator('.editor-change-list')).to_contain_text('valorRevisado');page.locator('[data-review-apply]').click()
   page.wait_for_function('__qa.editor.getValue().includes("println(valorRevisado)")');assert (ws/'vistaActual.n').read_text('utf-8')==original
   page.evaluate('__qa.editor.view.focus()');page.keyboard.press('Control+z');page.wait_for_function('(text)=>__qa.editor.getValue()===text',arg=original)
   checks.append('The actual nC extension renames the declaration and use through a reviewed edit in a split editor; Ctrl+Z restores the draft and disk is unchanged')
   assert not errors,errors;browser.close()
 finally:
  server.shutdown();server.server_close();f.shutdown();app.runner.shutdown();(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'details':details},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'errors':errors},ensure_ascii=False))
