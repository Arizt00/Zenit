import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from tests.test_git_conflicts import conflicted_project
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'qa-output/r17-git-conflicts-ui');out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-r17-conflicts-ui-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();git=conflicted_project(ws);original=(ws/'main.py').read_bytes();app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False});server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI}};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.locator('.activity-rail [data-view=git]').click();page.locator('[data-platform=git-conflicts]').click();expect(page.locator('.conflict-three-views .monaco-editor')).to_have_count(3);page.wait_for_function('__qa.platform.conflictsUI.result?.getValue().includes("<<<<<<<")');checks.append('Actual Git conflict opens ours, editable result and theirs in three separate editors')
    for width,height in [(1600,1000),(1280,720)]:
     page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(250);bounds=page.locator('.conflict-three-views>section').evaluate_all('els=>els.map(e=>e.getBoundingClientRect().toJSON())');assert max(x['y'] for x in bounds)-min(x['y'] for x in bounds)<1;assert max(x['height'] for x in bounds)-min(x['height'] for x in bounds)<1;assert bounds[-1]['right']<=width+1;page.screenshot(path=str(out/f'three-views-{width}.png'))
    page.locator('[data-conflict-use=ours]').click();page.wait_for_function('__qa.platform.conflictsUI.result.getValue().includes("ours")&&!__qa.platform.conflictsUI.result.getValue().includes("<<<<<<<")');textarea=page.locator('[data-conflict-editor=result] textarea');textarea.focus();page.keyboard.press('Control+z');page.wait_for_function('__qa.platform.conflictsUI.result.getValue().includes("<<<<<<<")');checks.append('Accepting a side is an undoable edit in the result buffer')
    page.keyboard.press('Control+a');page.keyboard.insert_text('print("merged in UI")\n');page.wait_for_timeout(500);page.evaluate('__qa.platform.conflictsUI.flush()');assert (ws/'main.py').read_bytes()==original;page.reload();page.wait_for_function('window.lumen?.platformReady');page.locator('.activity-rail [data-view=git]').click();page.locator('[data-platform=git-conflicts]').click();expect(page.locator('[data-conflict-status]')).to_have_text('Borrador recuperado');page.wait_for_function('__qa.platform.conflictsUI.result.getValue().includes("merged in UI")');checks.append('Result draft survives interface reload without changing the original working file')
    page.locator('[data-conflict-stage]').click();expect(page.locator('.conflict-saved')).to_contain_text('conflicto resuelto en Git',timeout=15000);assert not git('ls-files','-u').stdout;assert (ws/'main.py').read_text()=='print("merged in UI")\n';assert any(p.read_bytes()==original for p in (ws/'.lumen/conflicts').glob('*.before'));checks.append('Explicit save-and-resolve updates the actual index and keeps the prior file backup')
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print('PASS',checks,flush=True)
if __name__=='__main__':main()
