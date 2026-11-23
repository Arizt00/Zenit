"""Real nC scope/review/undo and the CTest/NCC explorer on disposable projects."""
import json,sys,tempfile,threading,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.project_kits import KITS
from tests.test_language_depth import NC
from playwright.sync_api import sync_playwright,expect


def main():
 out=ROOT/'qa-output/language-depth-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-language-depth-ui-') as temporary:
  base=Path(temporary);root=base/'Project with spaces';root.mkdir();text=NC+'\n'+NC.replace('vistaActual','otraVista');(root/'scopes.n').write_text(text,encoding='utf-8');(root/'smoke.n').write_text(NC,encoding='utf-8');(root/'test_python.py').write_text('def test_python(): pass\n')
  with zipfile.ZipFile(ROOT/'web/assets/extensions/nc-language-1.0.0-21v.zenit.6.vsix') as archive:(root/'lane.n').write_bytes(archive.read('extension/test-fixtures/machine_mode.nm'))
  for name,value in KITS['c']['files'].items():file=root/'c-project'/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(value,encoding='utf-8')
  app=Application(ROOT,root,data_dir=base/'profile');f=app.features;app.workspace.trusted=True
  review=f.extensions.inspect_file(ROOT/'web/assets/extensions/nc-language-1.0.0-21v.zenit.6.vsix');f.extensions.install(review['ticket'],True)
  f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'editor.autoLanguageServer':False,'files.autoSave':False,'security.confirmRoutineActions':False});f.studio.update({'onboarded':True});f.extension_runtime.start(app.workspace,'nc-lang.nc-language',True)
  plan=f.runtimes.plan(app.workspace,'c-project/src/main.c');task=app.runner.start(plan['commands'],root);job=app.runner.jobs[task['job']];deadline=time.monotonic()+90
  while not job.done and time.monotonic()<deadline:time.sleep(.05)
  assert job.done and job.code==0,job.output
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('__qa.openFile("scopes.n")');page.wait_for_function('__qa.editor.current==="scopes.n"')
    page.evaluate('()=>{__qa.editor.view.setPosition({lineNumber:21,column:23});__qa.editor.view.focus();__qa.editor.view.trigger("qa","editor.action.revealDefinition",{});}')
    page.wait_for_function('__qa.editor.view.getPosition().lineNumber===18');checks.append('F12 selects the declaration in the second nC container, not its namesake in the first')
    page.evaluate('()=>{__qa.editor.view.setPosition({lineNumber:21,column:23});__qa.editor.view.focus();void __qa.editor.view.getAction("editor.action.rename").run();}')
    box=page.locator('.rename-box input');box.wait_for(state='visible');box.fill('resultado');box.press('Enter');expect(page.locator('.editor-change-review')).to_be_visible(timeout=15000);expect(page.locator('.editor-change-list')).to_contain_text('scopes.n');page.locator('[data-review-apply]').click()
    expected=NC+'\n'+NC.replace('vistaActual','otraVista').replace('valor','resultado');page.wait_for_function('(value)=>__qa.editor.models.get("scopes.n").model.getValue()===value',arg=expected);assert (root/'scopes.n').read_text()==text
    page.evaluate('__qa.editor.view.focus()');page.keyboard.press('Control+z');page.wait_for_function('(value)=>__qa.editor.models.get("scopes.n").model.getValue()===value',arg=text);checks.append('F2 reviews and changes only the selected scope; Ctrl+Z restores it without writing user sources')
    page.evaluate('__qa.openFile("lane.n")');page.evaluate('()=>{__qa.editor.view.focus();void __qa.editor.view.getAction("editor.action.quickFix").run();}');page.get_by_text('Rename file to .nm (lane migration policy)',exact=True).click();page.wait_for_function('__qa.editor.current==="lane.nm"');assert not (root/'lane.n').exists() and (root/'lane.nm').is_file();assert (root/'scopes.n').read_text()==text;assert f.extension_runtime.snapshot()['hosts'][0]['running'];checks.append('The actual nC lane-migration quick fix renames the fixture through WorkspaceEdit without a constructor error')
    page.evaluate('__qa.platform.testsUI.open()')
    form=page.locator('.test-run-form');form.locator('[name=framework]').select_option('ncc');expect(page.locator('.test-inventory')).to_contain_text('smoke.n');expect(page.locator('.test-inventory')).not_to_contain_text('test_python')
    row=page.locator('.test-inventory-row').filter(has_text='smoke.n');row.locator('[data-test-single]').click();expect(page.locator('.test-command-review')).to_contain_text('prueba de humo');page.locator('[data-tests-confirm]').click();expect(page.locator('.test-run-report [data-test-status=passed]').first).to_be_visible(timeout=30000);checks.append('NCC smoke tests have their own inventory, explicit command review and linked source result')
    form.locator('[name=framework]').select_option('ctest');expect(form.locator('.test-directory-label')).to_be_visible();expect(form.locator('[name=directory] option')).to_have_count(1);form.locator('button[type=submit]').click();page.locator('[data-tests-confirm]').click();expect(page.locator('.test-run-report')).to_contain_text('ctest');expect(page.locator('.test-run-report [data-test-status=passed]').first).to_be_visible(timeout=30000);checks.append('The generated CMake kit is discovered, built and tested with CTest through the actual UI')
    page.screenshot(path=str(out/'ctest-results.png'));assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
 (out/'report.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8');print(json.dumps({'checks':checks,'errors':errors},indent=2))


if __name__=='__main__':main()
