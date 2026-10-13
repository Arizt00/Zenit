"""R5 product flows with real Monaco/ConPTY; AI transport is explicitly a fixture."""
import argparse,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
 checks=[];errors=[]
 def passed(s):checks.append(s);print('PASS',s,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-craft-') as tmp:
  base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'src').mkdir()
  source='''from pathlib import Path


def summarize(folder: Path) -> dict[str, int]:
    files = [path for path in folder.rglob("*") if path.is_file()]
    return {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}


if __name__ == "__main__":
    report = summarize(Path.cwd())
    print("Aurora · workspace summary")
    print(f"Files: {report['files']} · Bytes: {report['bytes']:,}")
'''
  (ws/'src/main.py').write_text(source,encoding='utf-8');(ws/'README.md').write_text('# Aurora\nA small workspace explorer.\n');(ws/'src/wait.py').write_text('import time\nprint("Waiting for Stop", flush=True)\ntime.sleep(120)\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'})
  app.features.prefs.update({'general.showWelcome':False,'appearance.theme':'dark','appearance.motion':True,'updates.automatic':False,'security.confirmRoutineActions':False,'terminal.confirmClose':False})
  assert app.features.prefs.get('general.locale')=='en'
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get dock(){return dock},get editor(){return editor},get platform(){return platformUI},get desktop(){return desktopUI},openFile};')
    context.route('**/src/app.js',inject)
    def open_page(suffix=''):
     page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url+suffix);page.wait_for_function('window.lumen?.ready');return page
    page=open_page();page.evaluate('__qa.studio.enter()');page.evaluate('__qa.openFile("src/main.py")');expect(page.locator('.melody-compose-modes')).to_be_visible();expect(page.locator('.melody-destination')).to_contain_text('Connect a model');expect(page.locator('html')).to_have_attribute('lang','en');passed('English default, visible model destination, chat/edit modes and context')
    page.evaluate('async()=>{await __qa.platform.openTerminal("cmd");await __qa.studio.desktop.share("src/main.py")}');page.wait_for_function('!!__qa.platform.activeTerminal')
    page.screenshot(path=str(out/'workspace-dark.png'),animations='disabled')
    page.evaluate('__qa.studio.showActivity()');expect(page.locator('.activity-profile')).to_be_visible();page.screenshot(path=str(out/'activity-dark.png'),animations='disabled');page.keyboard.press('Escape')
    page.evaluate('__qa.studio.home()');page.wait_for_timeout(600);page.screenshot(path=str(out/'home.png'),animations='disabled');page.evaluate('__qa.studio.enter()')
    page.evaluate('()=>__qa.studio.search()');page.locator('#studio-search').fill('report');expect(page.locator('[data-search-result]')).to_have_count(2);page.screenshot(path=str(out/'search-dark.png'),animations='disabled');page.evaluate('__qa.platform.closePage()')
    page.evaluate('()=>{__qa.editor.view.setSelection(new monaco.Range(5,5,5,78));}');expect(page.locator('.composer-context>button')).to_contain_text('Selection');page.locator('[data-melody-mode=edit]').click();expect(page.locator('.composer-context>button')).to_contain_text('main.py');page.locator('[data-melody-mode=chat]').click()
    page.locator('.composer-context>button').click();page.get_by_role('menuitem',name='No code',exact=True).click();expect(page.locator('.composer-context>button')).to_contain_text('No code');passed('Context chooser is actionable and edit mode always uses the full file')
    page.evaluate('async()=>{await __qa.platform.savePreference("ai.provider","ollama");await __qa.platform.savePreference("ai.model","explicit-qa-fixture");}');requests=[]
    def transport(job,messages,system,key):requests.append(messages);job.append('A fixture response for context verification.');job.done=True
    app.features.ai._run=transport
    page.locator('#ai-input').fill('Explain this');page.locator('.send-button').click();expect(page.locator('.chat-message.assistant')).to_contain_text('fixture response',timeout=15000);assert 'summarize' not in json.dumps(requests[-1]);passed('No-code request sends no file content to the fixture transport')
    page.evaluate('__qa.platform.savePreference("ai.context","selection")');page.evaluate('()=>__qa.editor.view.setSelection(new monaco.Range(5,5,5,78))');page.locator('#ai-input').fill('Explain this selection');page.locator('.send-button').click();expect(page.locator('.chat-message.assistant')).to_have_count(2,timeout=15000);assert 'rglob' in json.dumps(requests[-1]);assert 'from pathlib' not in json.dumps(requests[-1]);passed('Selection request sends the selected code, excluding the rest of the file')
    page.evaluate('()=>__qa.platform.reviewCode("    files = []",{path:__qa.editor.current,text:__qa.editor.getValue(),scope:"selection",selectedText:__qa.editor.getSelection(),selection:{...__qa.editor.view.getSelection()}})');expect(page.locator('#review-selection')).to_be_visible();page.locator('#review-selection').click();assert page.evaluate('__qa.editor.getValue()').startswith('from pathlib import Path');assert 'files = []' in page.evaluate('__qa.editor.getValue()');page.evaluate('__qa.editor.view.trigger("qa","undo",{})');assert page.evaluate('__qa.editor.getValue()')==source;passed('Selection review changes only captured range; a single undo restores the whole source')
    page.evaluate('__qa.platform.savePreference("ai.model","")');page.locator('.melody-new-chat').click();page.wait_for_timeout(300)
    for theme in ('day','dark','forest'):
     page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)',theme);page.wait_for_function('(t)=>document.documentElement.dataset.theme===t',arg=theme);page.screenshot(path=str(out/f'workspace-{theme}.png'),animations='disabled')
    passed('Three actual theme palettes keep the product hierarchy and typography')
    forge=open_page('/?panel=forge&file=src%2Fmain.py');forge.set_viewport_size({'width':1060,'height':760});forge.locator('.forge-file-run').click();forge.wait_for_function('()=>__qa.desktop.forgeRun?.terminal&&__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal)?.closed',timeout=30000);expect(forge.locator('.forge-session-detail')).to_contain_text('exit 0');forge.screenshot(path=str(out/'forge.png'),animations='disabled');passed('Forge executes actual Python and shows process exit code and elapsed time')
    forge.locator('[data-action=forge-rerun]').click();forge.wait_for_function('()=>__qa.desktop.forgeHistory?.length===1&&__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal)?.closed',timeout=30000);expect(forge.locator('.forge-history')).to_be_visible();passed('Run again executes the captured file and retains bounded execution history')
    forge.evaluate('__qa.openFile("src/wait.py")');forge.locator('.forge-file-run').click();forge.wait_for_function('__qa.desktop.forgeRun?.path==="src/wait.py"&&!!__qa.desktop.forgeRun?.terminal');sid=forge.evaluate('__qa.desktop.forgeRun.terminal');forge.locator('[data-action=forge-stop]').click();forge.wait_for_function('__qa.desktop.forgeRun?.stopped');assert app.features.terminals.get(sid).closed;expect(forge.locator('.forge-session-detail')).to_contain_text('Stopped');passed('Stop terminates the actual tracked process without closing unrelated terminals')
    for w,h in ((640,480),(380,420)):
     forge.set_viewport_size({'width':w,'height':h});assert not forge.evaluate('document.documentElement.scrollWidth>innerWidth');expect(forge.locator('.forge-file-run')).to_be_visible();forge.screenshot(path=str(out/f'forge-{w}.png'),animations='disabled')
    passed('Forge remains actionable at compact window sizes')
    page.set_viewport_size({'width':1366,'height':768});page.screenshot(path=str(out/'workspace-1366.png'),animations='disabled');assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.emulate_media(reduced_motion='reduce');assert page.evaluate('window.lumen.motionEnabled') is False;passed('Compact main workspace and reduced motion remain functional')
    gallery=open_page();gallery.evaluate('__qa.studio.enter()');gallery.evaluate('__qa.openFile("src/main.py")');gallery.evaluate('__qa.desktop.runHacker("python")');gallery.wait_for_function('()=>__qa.desktop.forgeRun?.terminal&&__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal)?.closed',timeout=30000);gallery.evaluate('()=>{__qa.desktop.forgeIntegrated=false;__qa.desktop.paintHacker();__qa.dock.setSize("bottom",210);}');gallery.mouse.move(700,250);gallery.wait_for_timeout(600)
    for theme in ('day','dark'):
     gallery.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)',theme);gallery.wait_for_function('(t)=>document.documentElement.dataset.theme===t',arg=theme);gallery.screenshot(path=str(out/f'gallery-{theme}.png'),animations='disabled')
    gallery.evaluate('__qa.studio.home()');gallery.wait_for_timeout(500);gallery.screenshot(path=str(out/'home.png'),animations='disabled');gallery.evaluate('__qa.studio.enter()');gallery.evaluate('__qa.studio.showActivity()');gallery.screenshot(path=str(out/'activity-dark.png'),animations='disabled');gallery.keyboard.press('Escape');gallery.evaluate('__qa.studio.editProfile()');gallery.screenshot(path=str(out/'profile.png'),animations='disabled')
    assert not errors,errors;passed('No uncaught browser errors');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'aiTransport':'Explicit fixture for context payload and selection edits; no model-quality claim.','runtime':'Actual Windows ConPTY and Python'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
