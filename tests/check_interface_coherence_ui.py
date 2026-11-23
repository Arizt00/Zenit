"""Task-oriented UI, real moves/undo and live input on disposable projects."""
import json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/interface-coherence';out.mkdir(exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-interface-',ignore_cleanup_errors=True) as temporary:
  base=Path(temporary);root=base/'Project with spaces';root.mkdir();(root/'target').mkdir()
  for name,content in {'a.py':'value = 42\n','b.py':'value = 43\n','run.py':'print("READY>",flush=True)\nv=input()\nprint("RESULT="+v,flush=True)\n','phases.py':'print("PHASE_READY>",flush=True)\nv=input()\nprint("PHASE_RESULT="+v,flush=True)\n','test_sample.py':'import unittest\nclass Sample(unittest.TestCase):\n def test_value(self): self.assertEqual(6*7,42)\n'}.items():(root/name).write_text(content,encoding='utf-8')
  app=Application(ROOT,root,data_dir=base/'profile');ws=app.workspace;ws.trusted=True;f=app.features
  f.studio.update({'onboarded':True,'displayName':'Creator','pinnedProjects':[str(root)]});f.prefs.update({'general.showWelcome':False,'general.locale':'es','files.autoSave':False,'updates.automatic':False,'appearance.motion':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000},device_scale_factor=1.5,reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get studio(){return studio},get desktop(){return desktopUI},get editor(){return editor},get organizer(){return organizerUI},get temporary(){return temporaryTabs},get session(){return workbenchUI},openFile,renderTabs,activateFile,showMenu};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}')
    try:page.wait_for_function('window.lumen?.ready',timeout=15000)
    except Exception:
     print({'errors':errors,'startup':page.locator('#startup-status').inner_text(),'toasts':page.locator('#toasts').inner_text()},flush=True);page.screenshot(path=str(out/'startup-failure.png'));raise
    page.evaluate('async()=>{await __qa.openFile("a.py");await __qa.openFile("b.py");__qa.editor.models.get("a.py").model.setValue("value = 99\\n");__qa.activateFile("a.py");}')
    expect(page.locator('[data-tab="a.py"]')).to_have_attribute('aria-label','a.py · cambios sin guardar')
    page.evaluate('__qa.temporary.group("a.py","b.py")');expect(page.locator('.temporary-tab-folder')).to_have_attribute('aria-label','Carpeta temporal 1 · carpeta temporal · 2 archivos · 1 sin guardar')
    page.locator('[data-group-back]').focus();page.keyboard.press('Enter');expect(page.locator('[data-tab="a.py"]')).to_be_visible();expect(page.locator('[data-tab="b.py"]')).to_be_visible()
    page.evaluate('__qa.editor.detachedPaths.add("b.py");__qa.renderTabs()');expect(page.locator('.detached-files-chip')).to_be_visible();page.evaluate('__qa.editor.detachedPaths.delete("b.py");__qa.renderTabs()')
    checks.append('Modified files, temporary group return and separate-window indicator')
    a=page.locator('[data-file="a.py"]');b=page.locator('[data-file="b.py"]');a.click();b.click(modifiers=['Control']);box=a.bounding_box();destination=page.locator('[data-dir="target"]').bounding_box()
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.mouse.move(destination['x']+destination['width']/2,destination['y']+destination['height']/2,steps=15)
    expect(page.locator('.explorer-drop-preview')).to_contain_text('2 elementos · Mover a target');page.screenshot(path=str(out/'drag-destination.png'))
    page.keyboard.press('Escape');page.mouse.up();expect(page.locator('.explorer-drop-preview')).to_be_hidden();assert (root/'a.py').is_file() and (root/'b.py').is_file()
    a.focus();page.keyboard.press('Alt+m');expect(page.locator('.organizer-destination-form')).to_be_visible();page.locator('.organizer-destination-form select').select_option('target');page.locator('.organizer-destination-form .primary-button').click()
    page.wait_for_function('__qa.editor.models.has("target/a.py")');assert (root/'target/a.py').read_text('utf-8')=='value = 42\n';assert page.evaluate('__qa.editor.models.get("target/a.py").model.getValue()')=='value = 99\n'
    page.locator('[data-selection-undo]').click();page.wait_for_function('__qa.editor.models.has("a.py")');assert (root/'a.py').read_text('utf-8')=='value = 42\n';assert page.evaluate('__qa.editor.models.get("a.py").model.getValue()')=='value = 99\n'
    checks.append('Real multiple-file drag destination, Escape, keyboard move and undo preserve unsaved text')
    page.evaluate('async()=>{await __qa.openFile("run.py");__qa.editor.activeTabGroup=null;__qa.renderTabs()}');page.locator('.run-button').click();page.wait_for_function('__qa.desktop.forgeRun?.terminal')
    identity=page.evaluate('__qa.platform.activeTerminal');terminal=f.terminals.get(identity);deadline=time.monotonic()+20
    while 'READY>' not in terminal.output and time.monotonic()<deadline:time.sleep(.03)
    assert 'READY>' in terminal.output
    page.evaluate('__qa.openFile("a.py")');expect(page.locator('.console-context strong')).to_have_text('run.py');expect(page.locator('.console-context-state')).to_have_text('En ejecución')
    page.locator('[data-console-input]').click();page.keyboard.type('18');page.keyboard.press('Enter');deadline=time.monotonic()+15
    while not terminal.closed and time.monotonic()<deadline:time.sleep(.03)
    assert terminal.closed and terminal.code==0 and 'RESULT=18' in terminal.output
    expect(page.locator('.console-context-state')).to_have_text('Finalizada');expect(page.locator('[data-console-input]')).to_be_disabled();page.screenshot(path=str(out/'execution-context.png'))
    checks.append('Console tracks its program after switching editor, accepts input and reflects process completion')
    original_plan=f.runtimes.plan
    def phases_plan(workspace,path,**kwargs):
     result=original_plan(workspace,path,**kwargs)
     if path=='phases.py' and not kwargs.get('check'):result['commands'].insert(0,[sys.executable,'-c','import time; time.sleep(1.2)'])
     return result
    f.runtimes.plan=phases_plan
    page.evaluate('__qa.openFile("phases.py")');expect(page.locator('.run-button')).to_have_attribute('data-action','run');page.locator('.run-button').click()
    expect(page.locator('.console-context-state')).to_have_text('Preparando');expect(page.locator('#terminal-input')).to_be_disabled();expect(page.locator('[data-console-input]')).to_be_disabled()
    expect(page.locator('.console-context-state')).to_have_text('En ejecución',timeout=20000);page.locator('[data-console-input]').click();page.keyboard.type('9');page.keyboard.press('Enter');expect(page.locator('.console-context-state')).to_have_text('Finalizada',timeout=10000)
    f.runtimes.plan=original_plan;checks.append('Preparation disables program input until execution takes ownership')
    page.evaluate('__qa.session.openSpaces()');page.locator('.saved-space-form input').fill('Revisión');page.locator('.saved-space-form .primary-button').click();expect(page.locator('[data-space-pin="0"]')).to_be_visible();page.locator('[data-space-pin="0"]').click();expect(page.locator('[data-space-pin="0"]')).to_have_attribute('aria-pressed','true');page.locator('#modal [data-action=close-modal]').click()
    page.evaluate('__qa.studio.home()');expect(page.locator('[data-start-session]')).to_be_visible();expect(page.locator('[data-start-pin]').first).to_contain_text('Revisión');page.locator('.welcome-history-search input').fill('run.py');expect(page.locator('.welcome-recent')).to_have_count(1);expect(page.locator('.welcome-recent')).to_contain_text('run.py');page.screenshot(path=str(out/'home-light.png'))
    checks.append('Home retains identity, recovery, pinned project/space and searchable recent files')
    page.locator('[data-start-activity]').click();page.locator('[data-activity-tab=projects]').click();page.locator('[data-activity-menu]').first.click();expect(page.locator('#popover')).to_contain_text('Desfijar proyecto');page.keyboard.press('Escape');page.locator('.activity-work-button').click();expect(page.locator('.activity-work-list')).to_contain_text('run.py');before=len(f.terminals.sessions);page.locator('[data-activity-result]').filter(has_text='run.py').first.click();expect(page.locator('.code-detail-body')).to_contain_text('RESULT=18');assert len(f.terminals.sessions)==before;page.screenshot(path=str(out/'activity-result.png'))
    expect(page.locator('.code-detail-heading small')).to_have_text('Resultado de ejecución');checks.append('Activity opens recorded execution in persistent detail without repeating it')
    page.evaluate('__qa.platform.testsUI.open()');page.locator('.test-run-form button[type=submit]').click();page.locator('[data-tests-confirm]').click();page.wait_for_function('document.querySelectorAll(".test-result-row").length===1',timeout=30000)
    page.evaluate('__qa.studio.home()');page.locator('[data-start-activity]').click();page.locator('.activity-work-button').click();before=len(f.terminals.sessions);page.locator('[data-activity-result]').filter(has_text='unittest').first.click();expect(page.locator('.code-detail-heading small')).to_have_text('Resultado de pruebas');expect(page.locator('.code-detail-body')).to_contain_text('OK');assert len(f.terminals.sessions)==before
    page.evaluate('()=>{const record=__qa.editor.models.get("a.py");window.reviewResult=__qa.platform.reviewedEdits.apply([{path:"a.py",before:record.model.getValue(),after:"value = 101\\n",revision:record.revision}]);}');page.locator('[data-review-apply]').click();page.wait_for_function('__qa.platform.reviewedEdits.last?.state==="applied"')
    page.evaluate('__qa.studio.home()');page.locator('[data-start-activity]').click();page.locator('.activity-work-button').click();page.locator('[data-activity-result]').filter(has_text='Conjunto de cambios revisado').click();expect(page.locator('.code-detail-heading small')).to_have_text('Cambios revisados');expect(page.locator('.code-detail-body')).to_contain_text('value = 99');expect(page.locator('.code-detail-body')).to_contain_text('value = 101');assert (root/'a.py').read_text('utf-8')=='value = 42\n'
    checks.append('Activity returns to real unittest results and a reviewed change snapshot without running or saving again')
    page.evaluate('async()=>{await __qa.platform.savePreference("appearance.helpContrast",true);__qa.showMenu(document.querySelector(".new-tab"),[{label:"Una acción",icon:"code",run(){}}],"Menú de prueba")}');expect(page.locator('html')).to_have_attribute('data-help-contrast','solid');assert page.locator('#popover').evaluate('(n)=>getComputedStyle(n).backdropFilter')=='none';page.keyboard.press('Escape')
    page.evaluate('__qa.platform.savePreference("appearance.helpContrast",false)');expect(page.locator('html')).to_have_attribute('data-help-contrast','glass');checks.append('Optional opaque help surfaces persist while 35% transparency remains the default')
    for theme in ['dark','day']:
     page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)',theme)
     for width,height in [(1600,1000),(1024,768),(640,480),(800,360)]:
      page.set_viewport_size({'width':width,'height':height});page.evaluate('__qa.studio.home()');expect(page.locator('.welcome-history-search input')).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
      page.screenshot(path=str(out/f'home-{theme}-{width}x{height}.png'))
    checks.append('Light/dark layouts, reduced motion and 1.5 device scale at four window sizes')
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'passed':True,'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)

if __name__=='__main__':main()
