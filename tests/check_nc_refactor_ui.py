"""F12/F2, reviewed cross-module nC changes, undo and compiler execution."""
import json,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import LumenServer
from tests.test_nc_refactor import NcRefactorTests
from tests.test_nc_project import MAIN,HELPER
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/nc-project-refactor-ui';out.mkdir(exist_ok=True);case=NcRefactorTests();case.setUp();app=case.app;f=case.f;checks=[];errors=[]
 f.studio.update({'onboarded':True});f.prefs.update({'general.showWelcome':False,'general.locale':'es','editor.autoLanguageServer':False,'updates.automatic':False,'files.autoSave':False})
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get ed(){return editor},get p(){return platformUI},get preview(){return previewUI},openFile};')
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('__qa.openFile("main.n")');page.wait_for_function('__qa.ed.current==="main.n"')
   def select_answer():page.evaluate('()=>{const m=__qa.ed.view.getModel();__qa.ed.view.setPosition(m.getPositionAt(m.getValue().indexOf("answer")+1));__qa.ed.view.focus();}')
   select_answer();page.evaluate('__qa.ed.view.trigger("qa","editor.action.revealDefinition",{})');page.wait_for_function('__qa.ed.current==="Helper.n"');assert page.evaluate('__qa.ed.view.getPosition().column')==HELPER.index('answer')+1;checks.append('F12 resolves the actual exported declaration in compact source after use imports')
   page.evaluate('__qa.openFile("main.n")');select_answer()
   def rename():
    page.evaluate('void __qa.ed.view.getAction("editor.action.rename").run()');box=page.locator('.rename-box input');box.wait_for(state='visible');box.fill('result');page.evaluate('async()=>{const state=await __qa.p.api("/extensions/runtime");state.hosts[0].unsupportedApis=["qa.optionalApi"];const original=monaco.languages.registerRenameProvider;let replacements=0;monaco.languages.registerRenameProvider=(...args)=>{replacements++;return original(...args);};try{__qa.preview.registerExtensions(state.hosts);}finally{monaco.languages.registerRenameProvider=original;}if(replacements)throw Error("Status refresh replaced a live rename provider");}');box.press('Enter');expect(page.locator('.editor-change-review')).to_be_visible(timeout=30000)
   rename();expect(page.locator('.editor-change-list')).to_contain_text('Helper.n');expect(page.locator('.editor-change-list')).to_contain_text('main.n');page.evaluate('async()=>{await Promise.all(document.querySelector(".modal-backdrop").getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{})));}');page.screenshot(path=str(out/'review.png'));page.locator('[data-review-apply]').click()
   page.wait_for_function('()=>["main.n","Helper.n"].every(p=>__qa.ed.models.get(p).model.getValue().includes("result"))');assert (case.project/'Helper.n').read_text()==HELPER;assert (case.project/'main.n').read_text()==MAIN;checks.append('Refreshing optional API status while the F2 input is open keeps the active provider');checks.append('F2 checks both complete project candidates with NCC, then reviews two files without saving')
   page.evaluate('__qa.ed.view.focus()');page.keyboard.press('Control+z');page.wait_for_function('(original)=>["main.n","Helper.n"].every((p,i)=>__qa.ed.models.get(p).model.getValue()===original[i])',arg=[MAIN,HELPER]);checks.append('Ctrl+Z restores the reviewed module and its caller together')
   page.keyboard.press('Control+Shift+z');page.wait_for_function('()=>__qa.ed.models.get("Helper.n").model.getValue().includes("result")');page.keyboard.press('Control+z');page.wait_for_function('(text)=>__qa.ed.models.get("main.n").model.getValue()===text',arg=MAIN);checks.append('Redo and a second undo preserve both module buffers')
   select_answer();rename();page.evaluate('__qa.ed.models.get("Helper.n").model.setValue(__qa.ed.models.get("Helper.n").model.getValue().replace("42","43"))');page.locator('[data-review-apply]').click();expect(page.locator('.editor-change-status')).to_contain_text('cambió');expect(page.locator('.editor-change-review')).to_be_visible();assert page.evaluate('__qa.ed.models.get("main.n").model.getValue()')==MAIN;page.locator('[data-review-cancel]').click();checks.append('Editing a peer buffer during review rejects the stale rename and preserves the edit')
   page.evaluate('(text)=>__qa.ed.models.get("Helper.n").model.setValue(text)',HELPER);select_answer();rename();(case.project/'Helper.n').write_text(HELPER.replace('42','44'));page.locator('[data-review-apply]').click();expect(page.locator('.editor-change-status')).to_contain_text('camb');page.locator('[data-review-cancel]').click();checks.append('A saved dependency change also blocks the review before applying')
   assert not errors,errors;browser.close()
  # Execute a renamed disposable project with the selected NCC, not CMake.
  (case.project/'main.n').write_text(MAIN.replace('answer','result'));(case.project/'Helper.n').write_text(HELPER.replace('answer','result'))
  plan=f.runtimes.plan(case.ws,'main.n');job=app.runner.jobs[app.runner.start(plan['commands'],case.project,timeout=35)['job']];deadline=time.monotonic()+40
  while not job.done and time.monotonic()<deadline:time.sleep(.02)
  assert job.done and job.code==0 and '42' in job.output,job.output;assert not list(case.project.rglob('CMakeLists.txt'));checks.append('The reviewed rename executes through the real NCC project pipeline and returns 42 without CMake')
 finally:server.shutdown();server.server_close();case.tearDown()
 (out/'report.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)

if __name__=='__main__':main()
