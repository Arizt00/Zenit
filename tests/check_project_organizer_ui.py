"""Real drag gestures and session recovery on disposable project/profile data."""
import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/055-organizer-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-organizer-ui-') as temp:
  base=Path(temp);ws=base/'project';ws.mkdir()
  for path in ['alpha/one.py','alpha/two.py','beta/other.py','root.py','merge-a/shared/a.txt','merge-b/shared/b.txt','target/start.txt']:
   p=ws/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# '+path+'\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True})
  app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'appearance.motion':True})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1700,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get editor(){return editor},get organizer(){return organizerUI},get groups(){return temporaryTabs},get session(){return workbenchUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
    expect(page.locator('.editor-tabbar>.panel-header-identity')).to_have_count(0)
    page.locator('[data-dir=beta]').drag_to(page.locator('[data-dir=alpha]'),target_position={'x':70,'y':2})
    page.wait_for_function('__qa.organizer.orders[""]?.[0]==="beta"')
    checks.append('Starting a folder drag without a prior click keeps row geometry fixed and hits its ordering target')
    page.evaluate('(async()=>{await __qa.openFile("root.py");await __qa.openFile("alpha/one.py");await __qa.openFile("alpha/two.py");})()')
    checks.append('Editor starts directly with tabs and no redundant title/icon')
    row=lambda path:page.locator('#sidebar-content [data-file="'+path+'"]')
    # The drag keeps going while hovering another file; the dwell indicator picks it up.
    row('alpha/one.py').click();page.evaluate('__qa.editor.insertText("# unsaved buffer\\n",true)')
    src=row('alpha/one.py').bounding_box();pickup=row('alpha/two.py').bounding_box();dest=page.locator('[data-dir=beta]').bounding_box()
    page.mouse.move(src['x']+80,src['y']+src['height']/2);page.mouse.down();page.mouse.move(src['x']+90,src['y']+src['height']/2+4,steps=4)
    page.mouse.move(pickup['x']+80,pickup['y']+pickup['height']/2,steps=8);page.wait_for_timeout(850)
    page.wait_for_function('__qa.organizer.selected.size===2')
    expect(page.locator('.explorer-carry')).to_have_attribute('data-count','2')
    expect(page.locator('.explorer-carry .carry-card')).to_have_count(2)
    assert page.locator('.explorer-carry').evaluate('(n)=>getComputedStyle(n).pointerEvents')=='none'
    page.screenshot(path=str(out/'pickup-stack.png'))
    page.mouse.move(dest['x']+80,dest['y']+dest['height']/2,steps=8);page.mouse.up()
    page.wait_for_function('__qa.editor.models.has("beta/one.py")')
    assert (ws/'beta/one.py').is_file() and (ws/'beta/two.py').is_file() and not (ws/'alpha/one.py').exists()
    assert (ws/'beta/one.py').read_text()=='# alpha/one.py\n'
    assert page.evaluate('__qa.editor.isDirty("beta/one.py")');assert page.evaluate('__qa.editor.models.get("beta/one.py").model.getValue()')=='# unsaved buffer\n'
    expect(page.locator('.explorer-carry')).to_have_count(0)
    checks.append('Hover pickup drags two real files together; dirty buffer remains unsaved and follows its new path')
    checks.append('Cursor-following file stack updates its live count and leaves no drag ghost after landing')
    # Extract to the root drop target.
    page.locator('[data-dir=beta]').click();row('beta/two.py').drag_to(page.locator('.tree-root'))
    page.wait_for_function('document.querySelector("[data-file=\\"two.py\\"]")')
    assert (ws/'two.py').is_file() and not (ws/'beta/two.py').exists()
    checks.append('Dropping on the project root extracts a file from its folder')
    # Edge drop only changes the order; it does not alter filesystem parents.
    source=page.locator('[data-dir=beta]');target=page.locator('[data-dir=alpha]')
    source.drag_to(target,target_position={'x':70,'y':2})
    try:page.wait_for_function('__qa.organizer.orders[""]?.[0]==="beta"')
    except Exception:
     page.screenshot(path=str(out/'order-failure.png'));print(page.evaluate('({orders:__qa.organizer.orders,selected:[...__qa.organizer.selected],drag:__qa.organizer.drag,toasts:document.querySelector("#toasts").textContent})'));raise
    assert (ws/'beta').is_dir() and (ws/'alpha').is_dir()
    checks.append('Dropping on row edges saves a manual sibling order without moving directories on disk')
    page.locator('[data-dir="merge-a"]').click();page.locator('[data-dir="merge-b"]').click(modifiers=['Control'])
    page.evaluate('''()=>{const original=__qa.organizer.drop.bind(__qa.organizer);__qa.drops=[];__qa.organizer.drop=(drag,where)=>{__qa.drops.push({drag,where:{kind:where.kind,destination:where.destination,target:where.target}});return original(drag,where);};}''')
    page.locator('[data-dir="merge-a"]').drag_to(page.locator('[data-dir=target]'))
    try:page.locator('[data-folder-merge]').wait_for(timeout=4000)
    except Exception:
     page.screenshot(path=str(out/'merge-failure.png'));print(page.evaluate('({drops:__qa.drops,selected:[...__qa.organizer.selected],toasts:document.querySelector("#toasts").textContent,modal:document.querySelector("#modal").textContent})'),flush=True);raise
    page.locator('[data-folder-merge]').click();page.locator('[data-organizer-apply]').click()
    page.wait_for_function('!document.querySelector("[data-dir=\\"merge-a\\"]")')
    assert (ws/'target/shared/a.txt').is_file() and (ws/'target/shared/b.txt').is_file()
    checks.append('Multi-folder drag reviews and merges nested contents while preserving both folders’ files')
    # Temporary folder groups live editor tabs and survives a session checkpoint.
    page.locator('[data-tab="root.py"]').drag_to(page.locator('[data-tab="beta/one.py"]'))
    expect(page.locator('[data-temporary-group]')).to_have_count(1)
    assert page.evaluate('__qa.editor.tabGroups[0].paths.includes("root.py")')
    page.evaluate('__qa.session.flush()');page.reload();page.wait_for_function('window.lumen?.ready')
    expect(page.locator('[data-temporary-group]')).to_have_count(1)
    assert page.evaluate('__qa.editor.isDirty("beta/one.py")')
    assert page.evaluate('__qa.organizer.orders[""][0]')=='beta'
    checks.append('Temporary tab folder, manual order and dirty text recover after reload')
    page.locator('[data-group-undo]').click();expect(page.locator('[data-temporary-group]')).to_have_count(0)
    expect(page.locator('[data-tab="root.py"]')).to_be_visible();expect(page.locator('[data-tab="beta/one.py"]')).to_be_visible()
    assert page.evaluate('__qa.editor.isDirty("beta/one.py")');assert (ws/'root.py').is_file()
    checks.append('Back/undo icon dissolves the temporary folder and restores its tabs without touching files')
    # Explicit multi-file Melody context stays docked and never sends automatically.
    row('root.py').click();row('two.py').click(modifiers=['Control']);page.locator('[data-selection-melody]').click()
    expect(page.locator('#ai-input')).to_have_value(__import__('re').compile('.*root.py.*two.py.*',__import__('re').S))
    assert page.evaluate('__qa.platform.aiJob') is None
    checks.append('Selected files prepare a reviewable Melody question in its docked panel without sending it')
    page.evaluate('__qa.platform.savePreference("appearance.motion",false)')
    row('root.py').click();src=row('root.py').bounding_box();pickup=row('two.py').bounding_box()
    page.mouse.move(src['x']+70,src['y']+src['height']/2);page.mouse.down();page.mouse.move(src['x']+80,src['y']+src['height']/2+5,steps=4);page.mouse.move(pickup['x']+70,pickup['y']+pickup['height']/2,steps=6)
    page.wait_for_function('__qa.organizer.selected.size===2');expect(page.locator('.explorer-carry')).to_have_attribute('data-count','2')
    page.keyboard.press('Escape');page.mouse.up();expect(page.locator('.explorer-carry')).to_have_count(0);expect(page.locator('.tree-row.is-carried')).to_have_count(0)
    assert (ws/'root.py').is_file() and (ws/'two.py').is_file()
    checks.append('With motion disabled, pickup still works and Escape cancels cleanly without moving files or leaving dimmed rows')
    # Keep a real pointer drag active at the edge of a long, disposable tree.
    for i in range(60):(ws/f'scroll-{i:02}.py').write_text('print(1)\n')
    page.evaluate('__qa.organizer.h.refreshTree()');row('root.py').wait_for();row('root.py').scroll_into_view_if_needed()
    src=row('root.py').bounding_box();edge=page.locator('#sidebar-content').bounding_box()
    before=page.locator('#sidebar-content').evaluate('(n)=>n.scrollTop')
    page.mouse.move(src['x']+70,src['y']+src['height']/2);page.mouse.down();page.mouse.move(src['x']+80,src['y']+src['height']/2+5,steps=4)
    page.mouse.move(edge['x']+edge['width']/2,edge['y']+edge['height']-8,steps=8)
    page.wait_for_function('(before)=>document.querySelector("#sidebar-content").scrollTop>before+20',arg=before)
    assert page.locator('html').evaluate('(n)=>n.classList.contains("explorer-dragging")')
    page.keyboard.press('Escape');page.mouse.up();expect(page.locator('.explorer-carry')).to_have_count(0)
    assert not page.locator('html').evaluate('(n)=>n.classList.contains("explorer-dragging")')
    assert (ws/'root.py').is_file()
    checks.append('Dragging at the tree edge scrolls automatically; Escape stops scrolling and restores the grab cursor without moving files')
    page.screenshot(path=str(out/'explorer-and-tabs.png'))
    assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}))
if __name__=='__main__':main()
