import json,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.test_extension_webview_lifecycle import WebviewLifecycle
from backend.server import LumenServer
from playwright.sync_api import sync_playwright,expect

out=ROOT/'qa-output/r17-webview-recovery';out.mkdir(exist_ok=True)
case=WebviewLifecycle();case.setUp();app=case.app;server=None;checks=[];errors=[]
try:
 (app.workspace.root/'main.py').write_text('print("editor recovered")\n')
 app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'updates.automatic':False})
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
  try:
   page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
   page.locator('[data-file="main.py"]').click();expect(page.locator('.extension-webview-tab')).to_have_count(0);checks.append('Provider activation leaves the current editor visible and creates no webview tabs')
   case.call('qa.background');expect(page.locator('.extension-webview-tab')).to_have_count(1);expect(page.locator('.extension-webview-surface.active')).to_have_count(0);checks.append('A background panel with preserveFocus leaves the editor active')
   case.call('qa.sidebar.focus');expect(page.locator('.extension-webview-surface.active')).to_be_visible();expect(page.frame_locator('.extension-webview-surface.active iframe').locator('h1')).to_have_text('Requested view');checks.append('Explicit focus resolves and renders the requested webview')
   page.locator('#file-tabs [data-tab="main.py"]').click();expect(page.locator('.extension-webview-surface.active')).to_have_count(0);expect(page.locator('#editor-mount')).to_be_visible();checks.append('Clicking the file tab hides the extension and restores the editor')
   page.locator('.extension-webview-tab').filter(has_text='Vista solicitada').click();expect(page.locator('.extension-webview-surface.active')).to_be_visible()
   page.locator('.extension-webview-surface.active').get_by_role('button',name='Cerrar panel de extensión').click();expect(page.locator('.extension-webview-tab')).to_have_count(1)
   case.call('qa.sidebar.focus');expect(page.locator('.extension-webview-surface.active')).to_be_visible();checks.append('Closing a view and opening it again recreates its provider correctly')
   page.locator('#file-tabs [data-tab="main.py"]').click()
   page.keyboard.press('Control+Shift+p');page.locator('#palette-input').fill('>Abrir qa.tree');page.locator('.palette-result').filter(has_text='Abrir qa.tree').click();expect(page.locator('.extension-tree-view')).to_have_count(1);expect(page.locator('.extension-tree-view')).to_contain_text('Actual node');checks.append('A tree focus command opens only its own real provider and nodes')
   page.locator('[data-platform="close-page"]').click()
   page.keyboard.press('Control+Shift+p');page.locator('#palette-input').fill('>Abrir Árbol pendiente');page.locator('.palette-result').filter(has_text='Abrir Árbol pendiente').click();expect(page.locator('.extension-tree-view')).to_have_count(1);expect(page.locator('.extension-tree-view')).to_contain_text('todavía no ha registrado');checks.append('A declared view without a provider reports its real state without killing the extension')
   page.locator('[data-platform="close-page"]').click();page.screenshot(path=str(out/'editor-preserved.png'));assert not errors,errors
  except BaseException:page.screenshot(path=str(out/'failure.png'));raise
  finally:browser.close()
finally:
 if server:server.shutdown();server.server_close()
 case.tearDown();(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2))
print('PASS',checks,flush=True)
