"""Real test/replay/edit workflows with a deterministic model-response fixture."""
import json,re,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/investigations';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-research-ui-',ignore_cleanup_errors=True) as temporary:
  base=Path(temporary);ws=base/'project';ws.mkdir()
  before='def answer():\n return 42\n\n# stable note\nmarker=1\n';broken=before.replace('return 42','return 0')
  (ws/'calc.py').write_text(before);(ws/'test_calc.py').write_text('import unittest,calc\nclass Check(unittest.TestCase):\n def test_answer(self): self.assertEqual(calc.answer(),42)\n')
  app=Application(ROOT,ws,data_dir=base/'profile');f=app.features;app.workspace.trusted=True
  f.studio.update({'onboarded':True});f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'files.autoSave':False,'appearance.motion':False,'ai.provider':'ollama','ai.model':'research-fixture'})
  def run_tests():
   task=f.tests.start(app.workspace,{'framework':'unittest','consent':True});deadline=time.monotonic()+20
   while f.tests.active(f.tests.runs[task['run']]) and time.monotonic()<deadline:time.sleep(.03)
   assert f.tests.runs[task['run']]['result'];return task
  passed=run_tests();(ws/'calc.py').write_text(broken);failed=run_tests();server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get p(){return platformUI},get editor(){return editor},openFile};')
    page.route('**/src/app.js',inject)
    model_answer=json.dumps({'interpretation':'Candidate: calc changed from 42 to 0. The captured test fails; the proposal still needs verification.','changes':[{'path':'calc.py','content':before.replace('marker=1','marker=2')}]})
    submitted=[]
    def model_start(route):
     body=route.request.post_data_json;assert len(body['question'])<=24000 and len(body['content'])<=64000;submitted.append(body);route.fulfill(json={'id':'research-model-fixture'})
    page.route('**/api/platform/ai/start',model_start);page.route('**/api/platform/ai/job?*',lambda route:route.fulfill(json={'done':True,'delta':model_answer,'offset':len(model_answer),'error':None,'cancelled':False}))
    page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("calc.py")')
    page.evaluate('__qa.p.testsUI.open()');page.locator('[data-investigate-test]').first.click();expect(page.locator('.research-origin-chain button')).to_have_count(7);expect(page.locator('.research-baseline-diff')).to_contain_text('calc.py');checks.append('A real failed test opens its seven-step provenance and a previously passing revision')
    page.locator('[data-origin-node="4"]').click();expect(page.locator('.research-node-detail')).to_contain_text('sha256');page.locator('[data-origin-node="2"]').click();expect(page.locator('.research-node-detail')).to_contain_text('test_calc.py')
    source=page.get_by_role('button',name='Leer la fuente capturada · calc.py',exact=True);source.click();expect(page.locator('.code-detail-body')).to_contain_text('return 0');page.get_by_role('button',name='Volver a la investigación',exact=True).click();expect(page.locator('.research-workspace')).to_be_visible();checks.append('Compiler fingerprints and frozen source can be inspected and returned to without editing')
    page.locator('[data-research-replay]').click();page.locator('.research-replay-form [name=variant]').select_option('baseline');page.locator('.research-replay-form .primary-button').click();expect(page.locator('.research-command-review')).to_contain_text('test_bridge');page.locator('[data-research-run]').click();expect(page.locator('.research-trial')).to_have_count(1,timeout=30000);expect(page.locator('.research-trial')).to_contain_text('Anterior aprobada');checks.append('Reviewed Lantern reproduction runs the earlier passing source twice in copies')
    # Only chosen captured files are sent; no current editor source or memory is attached.
    page.get_by_role('checkbox',name=re.compile(r'^calc\.py ')).check();page.locator('[data-research-prompt]').click();expect(page.locator('.research-prompt pre')).to_contain_text('changesSinceBaseline');page.locator('[data-research-send]').click();
    # Confirmation may be present in profiles configured for reviewed AI requests.
    confirm=page.get_by_role('button',name='Enviar esta petición',exact=True)
    try:confirm.wait_for(timeout=1000);confirm.click()
    except Exception:pass
    expect(page.locator('.research-hunks input')).to_have_count(2,timeout=15000);assert len(submitted)==1;assert 'changesSinceBaseline' in submitted[0]['content'] and submitted[0]['memory'] is False and submitted[0]['filePlan'] is False;checks.append('Model-response fixture becomes a proposal; only reviewed evidence is sent without live edits or conversation memory')
    page.locator('[data-research-hunk="0:1"]').uncheck();page.locator('[data-research-verify]').click();page.locator('.research-replay-form .primary-button').click();page.locator('[data-research-run]').click();expect(page.locator('.research-trial')).to_have_count(2,timeout=30000);expect(page.locator('.research-trial').last).to_contain_text('Propuesta');assert (ws/'calc.py').read_text()==broken;checks.append('Selected proposal fragments pass real tests in two copies and leave the project unchanged')
    expect(page.locator('[data-research-hunk="0:1"]')).not_to_be_checked();page.locator('[data-research-apply]').click();page.locator('[data-review-apply]').click();page.wait_for_function('__qa.editor.models.get("calc.py").model.getValue().includes("return 42")');assert page.evaluate('__qa.editor.models.get("calc.py").model.getValue()')==before;assert (ws/'calc.py').read_text()==broken
    assert page.evaluate('__qa.p.investigationsUI.canRestore(__qa.p.investigationsUI.result) && !__qa.p.investigationsUI.canRestore({id:"another-investigation"})')
    page.locator('[data-research-undo]').click();page.wait_for_function('__qa.editor.models.get("calc.py").model.getValue().includes("return 0")');assert page.evaluate('__qa.editor.models.get("calc.py").model.getValue()')==broken;checks.append('Accept one fragment, reject another and restore only this investigation set without saving the source')
    original_plan=f.tests.plan
    def delayed_plan(workspace,body,output=None):
     result=original_plan(workspace,body,output);result['commands'].insert(0,[sys.executable,'-c','import time;time.sleep(.4)']);result['preparation']+=1;return result
    f.tests.plan=delayed_plan
    page.locator('[data-research-replay]').click();page.locator('.research-replay-form .primary-button').click();page.locator('[data-research-run]').click();page.locator('.research-progress').wait_for();page.locator('#modal [data-action=close-modal]').click();page.evaluate('__qa.p.closePage()');deadline=time.monotonic()+15
    while any(j['state'] in ('queued','running') for j in f.hilo.jobs.values()) and time.monotonic()<deadline:time.sleep(.05)
    page.wait_for_timeout(350);assert page.evaluate('__qa.p.page') is None;f.tests.plan=original_plan;page.evaluate('__qa.p.investigationsUI.open({id:__qa.p.investigationsUI.result.id})');expect(page.locator('.research-trial')).to_have_count(3);checks.append('Completing background reproduction preserves editor focus after the progress panel is closed')
    page.locator('.toast-dismiss').evaluate_all('buttons=>buttons.forEach(button=>button.click())')
    page.screenshot(path=str(out/'investigation-light.png'));page.evaluate('__qa.p.savePreference("appearance.theme","dark")');page.screenshot(path=str(out/'investigation-dark.png'));page.set_viewport_size({'width':1000,'height':700});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'investigation-small.png'));checks.append('Light/dark styles and narrow layout retain panel alignment')
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'model':'Deterministic response fixture; no external model request','passed':True},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}),flush=True)
if __name__=='__main__':main()
