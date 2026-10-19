import json,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

base=ROOT/'qa-output/r17-extension-trials';ws=base/'project';out=base/'behavior';out.mkdir(exist_ok=True)
(ws/'main.py').write_text('value = 42\n');(ws/'Cargo.toml').write_text('[package]\nname="zenit-qa"\nversion="0.1.0"\n')
app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'updates.automatic':False,'editor.tabSize':4})
checks=[];errors=[];server=None
try:
 for eid in ('EditorConfig.EditorConfig','tamasfe.even-better-toml'):app.features.extension_runtime.start(app.workspace,eid,True)
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
  try:
   page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
   page.locator('[data-file="main.py"]').click();page.wait_for_function('monaco.editor.getModels().some(m=>m.uri.path.endsWith("main.py")&&m.getOptions().tabSize===2)',timeout=15000)
   checks.append('Real EditorConfig package applies indent_size=2 to the Monaco model')
   page.locator('[data-file="Cargo.toml"]').click();page.wait_for_function('window.lumen.activeFile==="Cargo.toml"');page.locator('.monaco-editor textarea').first.focus();page.keyboard.press('Shift+Alt+f')
   page.wait_for_function('monaco.editor.getModels().some(m=>m.uri.path.endsWith("Cargo.toml")&&m.getValue().includes(\'name = "zenit-qa"\'))',timeout=20000)
   assert 'name="zenit-qa"' in (ws/'Cargo.toml').read_text();checks.append('Real Even Better TOML formatter edits the buffer and leaves disk unchanged')
   page.keyboard.press('Control+z');page.wait_for_function('monaco.editor.getModels().some(m=>m.uri.path.endsWith("Cargo.toml")&&m.getValue().includes(\'name="zenit-qa"\'))');checks.append('Formatting remains one undoable editor transaction')
   runtime=app.features.extension_runtime
   result=runtime.request(app.workspace,{'id':'tamasfe.even-better-toml','method':'provide','kind':'symbols','document':{'path':'Cargo.toml','text':(ws/'Cargo.toml').read_text(),'language':'toml'}})
   assert result['items'],result;checks.append('Real TOML language server returns document symbols')
   folding=runtime.request(app.workspace,{'id':'tamasfe.even-better-toml','method':'provide','kind':'folding','document':{'path':'Cargo.toml','text':(ws/'Cargo.toml').read_text(),'language':'toml'}});assert folding['items'],folding;checks.append('Real TOML folding ranges serialize declared Region kinds without activation errors')
   page.screenshot(path=str(out/'editorconfig-toml.png'))
   page.locator('.activity-rail [data-action=extensions]').click();card=page.locator('[data-package-id="EditorConfig.EditorConfig"]');expect(card).to_be_visible();card.locator('.extension-verification').click();expect(page.locator('.extension-evidence')).to_contain_text('Monaco');page.locator('[data-action=close-modal]').first.click();card.locator('button[aria-label="Manage this extension"],button[aria-label="Gestionar esta extensión"]').click();expect(page.locator('#popover')).to_be_visible();expect(page.locator('.extension-results')).to_be_visible();card.locator('button[aria-label="Manage this extension"],button[aria-label="Gestionar esta extensión"]').click();expect(page.locator('#popover')).to_have_class(__import__('re').compile('hidden'));expect(page.locator('.extension-results')).to_be_visible();checks.append('Exact-package compatibility evidence is visible and extension actions toggle without leaving the extension page');page.screenshot(path=str(out/'verified-extensions.png'));assert not errors,errors
  except BaseException:
   page.screenshot(path=str(out/'failure.png'));print({k:h.logs[-5000:] for k,h in app.features.extension_runtime.hosts.items()},flush=True);raise
  finally:browser.close()
finally:
 if server:server.shutdown();server.server_close()
 app.features.shutdown();app.runner.shutdown();(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8')
print('PASS',checks,flush=True)
