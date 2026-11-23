"""Task-based visual and interaction checks on disposable project/profile data."""
import json,sys,tempfile,threading,time,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/055-experience-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-experience-') as td:
  base=Path(td);ws=base/'project';ws.mkdir()
  saved='value=int(input())\nprint(value+1)\n';(ws/'main.py').write_text(saved);(ws/'debug.py').write_text('value=1\nvalue=2\nprint(value)\n');(ws/'example.s').write_text('.intel_syntax noprefix\n.text\nmov rax, 1\nadd rax, 2\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
  app.features.studio.update({'onboarded':True,'recent':[{'path':'main.py','workspace':str(ws),'openedAt':'2026-10-20T13:00:00Z'},{'path':'other.py','workspace':str(base/'other'),'openedAt':'2026-10-19T13:00:00Z'}]})
  app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False,'files.autoSave':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},get studio(){return studio},get dock(){return dock},get profiles(){return workspaceProfiles},get organizer(){return organizerUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.studio.home()');expect(page.locator('#lumen-home')).to_be_visible()
    for width,height in [(1600,1000),(1100,720),(800,600)]:
     page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(150)
     scene=page.locator('.welcome-copy').bounding_box();recent=page.locator('.welcome-resume').bounding_box();assert scene['y']+scene['height']<=recent['y']+2,(width,height,scene,recent)
     for item in page.locator('.welcome-recent').all():
      if item.is_visible():box=item.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width
    page.set_viewport_size({'width':1600,'height':1000});page.screenshot(path=str(out/'home.png'));checks.append('Home keeps recent files and primary actions separated at 1600×1000, 1100×720 and 800×600')
    page.locator('[data-start-recent="0"]').click();page.wait_for_function('window.lumen.activeFile==="main.py"');checks.append('A real recent-file tile returns to its project and editor')
    page.evaluate('__qa.studio.showActivity()');expect(page.locator('.profile-activity-file')).to_have_count(2);page.locator('.activity-scope').click();expect(page.locator('.profile-activity-file')).to_have_count(1);page.screenshot(path=str(out/'activity.png'));checks.append('Activity filters the current project without deleting history or changing the profile')
    page.locator('#modal-close').click() if page.locator('#modal-close').count() else page.keyboard.press('Escape')
    page.evaluate('__qa.dock.show("assistant");__qa.editor.insertText("value=int(input())\\nprint(value+2)\\n",true)')
    page.locator('.melody-utilities-toggle').click();page.locator('[data-melody-task=countercheck]').click();page.locator('.countercheck-form textarea').fill('4\n');page.locator('.countercheck-form button[type=submit],.countercheck-form .primary-button').click();expect(page.locator('[data-countercheck-run]')).to_be_visible();page.locator('[data-countercheck-run]').click();expect(page.locator('.countercheck-report')).to_be_visible(timeout=30000)
    output=page.locator('.countercheck-columns article>pre').all_text_contents();assert [x.strip() for x in output]==['5','6'],output;page.screenshot(path=str(out/'countercheck.png'));page.locator('[data-countercheck-ask]').click();expect(page.locator('#ai-input')).to_have_value(re.compile('Contraprueba'));assert page.evaluate('!__qa.platform.aiJob');assert (ws/'main.py').read_text()==saved;checks.append('Contraprueba reviews then runs both real variants, preserves source and prepares evidence in docked Melody without sending it')
    page.locator('[data-lantern=rules]').first.click();page.locator('[name=inputEnabled]').check();page.locator('[name=stdin]').fill('4\n');page.locator('[name=verifyEnabled]').check();page.locator('[name=match]').select_option('exact');page.locator('[name=expectedOutput]').fill('6\n');page.locator('[name=timeout]').fill('5');page.locator('.lantern-rules .primary-button').click();page.evaluate('__qa.studio.lantern.action("start")');expect(page.locator('.lantern-verification[data-state=passed]')).to_be_visible(timeout=20000);assert page.locator('#lantern-inline>.lantern-output').bounding_box()['height']>=70;page.screenshot(path=str(out/'lantern.png'));page.evaluate('__qa.studio.lantern.action("stop")');checks.append('Lantern replays real stdin and displays passing rules without changing the saved source')
    page.evaluate('document.querySelector("#lantern-inline")?.remove(); __qa.studio.debug()');expect(page.locator('.debug-page')).to_be_visible();page.locator('#debug-file').select_option('debug.py');page.locator('.debug-intro').click();page.keyboard.press('F5');page.wait_for_function('__qa.studio.debugWorkspace.state?.status==="paused"');page.keyboard.press('F10');page.wait_for_function('__qa.studio.debugWorkspace.state?.line===2');page.keyboard.press('F10');page.wait_for_function('__qa.studio.debugWorkspace.state?.line===3');expect(page.locator('.variable-row.variable-changed')).to_contain_text('value');page.locator('[aria-label="Filtrar variables"]').fill('missing');expect(page.locator('.variable-row')).to_have_count(0);page.locator('[aria-label="Filtrar variables"]').fill('value');expect(page.locator('.variable-row')).to_have_count(1);page.screenshot(path=str(out/'debug.png'));page.evaluate('__qa.studio.debugWorkspace.command("stop")');checks.append('Real Python debugging uses F5/F10 and filters variables while highlighting values changed between pauses')
    (ws/'console.py').write_text('import sys\nprint("CONSOLE_READY",flush=True)\nprint("INPUT_BYTES="+str(len(sys.stdin.read())))\n')
    page.evaluate('__qa.platform.closePage()');console=page.locator('#terminal-input');console.fill('run console.py');console.press('Enter');expect(page.locator('#terminal-log')).to_contain_text('CONSOLE_READY',timeout=15000);console.fill('abc');console.press('Enter');console.fill(':eof');console.press('Enter');expect(page.locator('#terminal-log')).to_contain_text('INPUT_BYTES=4',timeout=10000);page.screenshot(path=str(out/'console.png'));checks.append('The actual console starts a runtime, forwards interactive input and closes stdin with :eof')
    page.evaluate('(async()=>{__qa.platform.closePage();await __qa.openFile("example.s");__qa.profiles.apply("assembly");})()');expect(page.locator('[data-asm=run]')).to_be_visible();page.wait_for_function('__qa.profiles.assembly.catalog!==undefined');page.locator('[data-asm=step]').click();expect(page.locator('.asm-registers')).to_be_visible(timeout=20000);page.locator('[data-asm=pin]').click();page.locator('[data-asm=step]').click();expect(page.locator('.asm-registers>div.changed')).not_to_have_count(0);page.locator('[aria-label="Filtrar registros"]').fill('rax');expect(page.locator('[data-register-name=rax]')).to_be_visible();page.screenshot(path=str(out/'laboratory.png'));checks.append('Real ASM stepping pins a reference and filters changed registers without writing the source')
    assert (ws/'main.py').read_text()==saved;assert not errors,errors
    checks.append('No browser exceptions or source-file writes')
    browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}))

if __name__=='__main__':main()
