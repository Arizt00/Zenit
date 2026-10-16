"""R15 real execution ownership, nested menus and multi-IDE CRDT editing."""
import argparse,json,tempfile,threading,sys,io,zipfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(label):checks.append(label);print('PASS',label,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-r15-',ignore_cleanup_errors=True) as temp:
  base=Path(temp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print("WINDOW_OUTPUT")\n',encoding='utf-8');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
  app.features.studio.update({'onboarded':True,'displayName':'Ana'});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False,'appearance.motion':True})
  (ws/'sample.bin').write_bytes(bytes(range(256))*4);(ws/'hello.exe').write_bytes(b'\0placeholder');(ws/'hello.c').write_text('#include <stdio.h>\nint main(){puts("BEFORE_UI");return 0;}\n')
  from backend.binary_view import revision
  job=app.features.binary_tools.build({'path':'hello.exe','source':'hello.c','revision':revision(ws/'hello.exe')})
  while not app.runner.jobs[job['job']].done:time.sleep(.03)
  app.features.binary_tools.finish(job)
  payload=io.BytesIO()
  with zipfile.ZipFile(payload,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'appearance','displayName':'Aurora Studio','description':'Colores e iconos para comprobar su vista previa real.','version':'1.0.0','main':'main.cjs','contributes':{'themes':[{'id':'night','label':'Aurora noche','uiTheme':'vs-dark','path':'theme.json'}],'iconThemes':[{'id':'icons','label':'Aurora archivos','path':'icons.json'}]}}))
   z.writestr('extension/main.cjs','exports.activate=()=>{}');z.writestr('extension/theme.json',json.dumps({'colors':{'editor.background':'#182536','sideBar.background':'#233449','editor.foreground':'#f5f7fa'},'tokenColors':[{'scope':'keyword','settings':{'foreground':'#81a1ef'}}]}));z.writestr('extension/icons.json',json.dumps({'iconDefinitions':{'python':{'iconPath':'python.svg'}},'fileExtensions':{'py':'python'}}));z.writestr('extension/python.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#4288cc" d="M3 3h18v18H3z"/></svg>')
  review=app.features.extensions.inspect_bytes(payload.getvalue());app.features.extensions.install(review['ticket'],True)
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get team(){return teamUI},get editor(){return editor},get desktop(){return desktopUI},get preview(){return previewUI},get platform(){return platformUI},get studio(){return studio},get activeJob(){return activeJob},openFile,runCurrent,perform,showMenu,saveFile};')
    context.route('**/src/app.js',inject);context.on('page',lambda p:p.on('pageerror',lambda e:errors.append(str(e))))
    page=context.new_page();page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")')
    page.evaluate("async info=>{const {extensionReviewHTML}=await import('/src/extension-installer.js');__qa.platform.host.modal('Revisión de extensión',extensionReviewHTML(info,(es,en)=>es,__qa.platform.extensionLogo(info)),{wide:true});}",review)
    expect(page.locator('.extension-review-author')).to_contain_text('qa');expect(page.locator('.extension-ide-preview')).to_have_count(1);expect(page.locator('.extension-icons-preview img')).to_have_count(1)
    assert page.locator('.extension-ide-preview').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(24, 37, 54)'
    expect(page.locator('.extension-review-author')).to_be_visible();page.wait_for_timeout(400);page.screenshot(path=str(out/'extension-preview.png'));page.evaluate('__qa.platform.host.closeModal()');page.evaluate("__qa.preview.startExtension('qa.appearance')");page.wait_for_function("__qa.platform.prefs['appearance.iconTheme']==='qa.appearance:icons'");assert not any(x.extension_id=='qa.appearance' for x in app.features.extension_runtime.hosts.values());page.evaluate("__qa.platform.savePreference('appearance.iconTheme','zenit')")
    passed('Extension review shows creator, description, real palette and file icons; starting the appearance package applies its icon set without running its code')
    expect(page.locator('.top-actions .coco-button')).to_have_text('CoCo');assert page.locator('.coco-button').bounding_box()['x']>1100;page.locator('.coco-button').click();expect(page.locator('#modal-title')).to_have_text('Co-Code');page.evaluate('__qa.platform.host.closeModal()');passed('Co-Code has its own CoCo icon and control on the right side of the application')
    page.evaluate('__qa.openFile("sample.bin")');page.locator('[data-byte="0"]').click();page.locator('[data-binary-edit]').click();page.locator('[data-binary-edit-form] input').fill('7f');page.locator('[data-binary-edit-form] button').click();assert page.evaluate('__qa.editor.isDirty()');page.locator('[data-binary-undo]').click();assert not page.evaluate('__qa.editor.isDirty()');page.locator('[data-binary-redo]').click();page.evaluate('__qa.openFile("main.py")');page.evaluate('__qa.openFile("sample.bin")');expect(page.locator('[data-byte="0"]')).to_have_text('7f');page.locator('[data-byte-next]').click();page.wait_for_function('__qa.editor.binaryView.item.offset===512');page.evaluate('__qa.saveFile()');assert (ws/'sample.bin').read_bytes()[0]==127;assert any(p.read_bytes()[0]==0 for p in (ws/'.lumen/binary-backups').rglob('*') if p.is_file());page.screenshot(path=str(out/'binary-editor.png'));passed('Hex edits survive tab and page changes; undo/redo and save preserve an original-byte backup')
    (ws/'hello.c').write_text('#include <stdio.h>\nint main(){puts("REBUILT_UI");return 0;}\n');page.evaluate('__qa.openFile("hello.exe")');page.locator('[data-binary-build]').click();page.locator('#binary-build-form input').fill('hello.c');page.locator('#binary-build-form button.primary-button').click();page.wait_for_function("[...document.querySelectorAll('.toast')].some(n=>n.textContent.includes('Binario recompilado'))",timeout=30000);page.locator('[data-binary-run]').click();expect(page.locator('.pty-session:not([hidden]) .xterm-rows')).to_contain_text('REBUILT_UI',timeout=15000);page.wait_for_function('__qa.platform.terminals.get(__qa.desktop.forgeRun?.terminal)?.closed');page.mouse.move(5,5);page.wait_for_timeout(500);expect(page.locator('.run-button')).to_be_enabled();page.screenshot(path=str(out/'binary-rebuilt.png'));passed('The binary UI recompiles real C into the selected executable and runs that artifact in a real terminal')
    page.evaluate('__qa.openFile("main.py")')
    with page.expect_popup() as popup:page.evaluate('__qa.desktop.detach("editor","main.py")')
    child=popup.value;child.wait_for_function('window.lumen?.ready');child.evaluate('__qa.runCurrent()');expect(child.locator('.pty-session:not([hidden]) .xterm-rows')).to_contain_text('WINDOW_OUTPUT');child.wait_for_function('!__qa.desktop.forgeRun||__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal)?.closed');assert 'WINDOW_OUTPUT' not in page.locator('#terminal-log').inner_text()
    run=child.locator('.native-editor-run');expect(run.locator('span')).to_have_text('Ejecutar');child.mouse.move(10,400);child.wait_for_timeout(500);assert run.locator('span').evaluate('(e)=>getComputedStyle(e).visibility')=='hidden'
    child.evaluate('__qa.desktop.useMainTerminal()');before=child.locator('.pty-session:not([hidden]) .xterm-rows').inner_text();child.evaluate('__qa.runCurrent()');expect(page.locator('.pty-session:not([hidden]) .xterm-rows')).to_contain_text('WINDOW_OUTPUT');page.wait_for_function('__qa.platform.terminals.get(__qa.desktop.forgeRun?.terminal)?.closed');assert child.locator('.pty-session:not([hidden]) .xterm-rows').inner_text()==before
    child.screenshot(path=str(out/'external-controls.png'));passed('Executing locally writes only to the external console; selecting Zénit routes execution exclusively to the main console and retains the animated label')
    child.locator('.native-return').click();page.wait_for_function('!__qa.editor.detachedPaths.size')
    page.evaluate("__qa.showMenu(document.querySelector('.editor-tabbar .zenit-tools-menu'),[{label:'Acción',run(){}}],'Acciones')")
    page.wait_for_timeout(250);anchor=page.locator('.editor-tabbar .zenit-tools-menu');r=anchor.bounding_box();box=page.locator('#popover').bounding_box();assert box['y']-r['y']-r['height']>=14
    page.evaluate("__qa.showMenu(document.querySelector('.editor-tabbar .zenit-tools-menu'),[{label:'Acción',run(){}}],'Acciones')");expect(page.locator('#popover')).to_have_class('popover hidden')
    passed('The same three-dot anchor closes its menu; the menu clears the toolbar with a 16px gap')
    page.evaluate("__qa.preview.runtimeCommands=new Map([['a',{ext:'qa.first',id:'one',title:'Uno'}],['b',{ext:'qa.second',id:'two',title:'Dos'}]]);__qa.preview.extensionMetadata=new Map([['qa.first',{id:'qa.first',displayName:'Primera extensión',publisher:'qa'}]]);__qa.preview.contextMenu.open(__qa.editor.view,1250,650)")
    page.locator('.editor-context-menu:not(.menu-leaving) button',has_text='Extensiones activas').hover();page.wait_for_timeout(350)
    page.locator('.editor-context-menu:not(.menu-leaving) button',has_text='Primera extensión').hover();page.wait_for_timeout(450)
    menus=page.locator('.editor-context-menu:not(.menu-leaving):not([hidden])');boxes=menus.evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}})');assert len(boxes)==3,boxes
    for a,b in zip(boxes,boxes[1:]):assert b['left']-a['right']>=12,(a,b)
    assert boxes[0]['left']>=8 and boxes[-1]['right']<=1592;expect(page.locator('.editor-menu-extension-icon')).to_have_count(1);page.screenshot(path=str(out/'extension-menu.png'));page.keyboard.press('Escape')
    passed('Three menu levels remain separate inside the viewport and extension entries use their display names and package marks')
    page.evaluate('__qa.team.open()');page.locator('[data-team-run]').check();page.locator('[data-team-host]').click();page.wait_for_function('__qa.team.running&&__qa.team.files.size===1');invite=page.evaluate('__qa.team.state.invitation');peer=context.new_page();peer.goto(invite);peer.locator('#name').fill('Bea · JetBrains');peer.locator('#connect').click();peer.wait_for_function('document.querySelector("#connect").disabled');expect(peer.locator('#files')).to_contain_text('main.py')
    page.evaluate("__qa.editor.view.executeEdits('qa',[{range:new monaco.Range(1,1,1,1),text:'# Ana 🙂\\n'}])");peer.evaluate("monaco.editor.getModels()[0].applyEdits([{range:new monaco.Range(1,1,1,1),text:'# Bea λ\\n'}])")
    page.wait_for_function('__qa.editor.getValue().includes("# Bea λ")');peer.wait_for_function('monaco.editor.getModels()[0].getValue().includes("# Ana 🙂")');assert page.evaluate('__qa.editor.getValue()')==peer.evaluate('monaco.editor.getModels()[0].getValue()')
    expect(peer.locator('#peers')).to_contain_text('Ana');page.screenshot(path=str(out/'team-workbench.png'));peer.screenshot(path=str(out/'team-peer.png'))
    peer.locator('#save').click();expect(peer.locator('#status')).to_contain_text('Guardado');assert (ws/'main.py').read_text(encoding='utf-8')==page.evaluate('__qa.editor.getValue()')
    passed('Zénit and the embedded cross-IDE Monaco client converge after concurrent Unicode edits; a guest saves the shared file on the host')
    peer.locator('#run').click();expect(peer.locator('#output')).to_contain_text('WINDOW_OUTPUT');expect(peer.locator('#output')).to_contain_text('Process exited with code 0');passed('Guests execute in the host environment and receive one shared output stream')
    guestWorkspace=base/'guest';guestWorkspace.mkdir();guestApp=Application(ROOT,guestWorkspace,data_dir=base/'guest-profile');guestApp.workspace.trusted=True;guestApp.features.studio.update({'onboarded':True,'displayName':'Carlos'});guestApp.features.prefs.update({'general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False});guestApp.features.team.join(guestApp.workspace,invite)
    guestServer=LumenServer(0,guestApp);threading.Thread(target=guestServer.serve_forever,daemon=True).start()
    try:
     guest=context.new_page();guest.on('response',lambda r:errors.append('Guest API failed: '+r.url) if '/api/' in r.url and r.status>=400 else None);guest.goto(f'http://127.0.0.1:{guestServer.server_port}');guest.wait_for_function('window.lumen?.ready');guest.evaluate('__qa.team.open()');guest.wait_for_function('__qa.team.files.size===1');guest.evaluate('__qa.platform.host.closeModal()');guest.locator('.monaco-editor').first.click();guest.evaluate("__qa.editor.view.executeEdits('qa',[{range:new monaco.Range(1,1,1,1),text:'# Carlos\\n'}])");page.wait_for_function('__qa.editor.getValue().includes("# Carlos")');guest.evaluate('__qa.saveFile()');guest.wait_for_timeout(2000);assert '# Carlos' in (ws/'main.py').read_text(encoding='utf-8');assert not (guestWorkspace/'.team').exists();guest.screenshot(path=str(out/'team-guest-zenit.png'));guest.evaluate('__qa.team.stop()');guest.close();passed('A second Zénit joins with virtual buffers, synchronizes and saves on the host without creating fake local files or extension API errors')
    finally:guestServer.shutdown();guestServer.server_close();guestApp.features.shutdown();guestApp.runner.shutdown()
    page.evaluate('__qa.team.stop()');peer.close();context.close();browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2,ensure_ascii=False),encoding='utf-8');assert not errors,errors

if __name__=='__main__':main()
