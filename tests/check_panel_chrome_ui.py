"""Shared panel headers over a real workbench and disposable profile."""
import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/panel-chrome';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];matrix=[]
 with tempfile.TemporaryDirectory(prefix='zenit-panel-chrome-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();source='int main(void) {\n    return 42;\n}\n';(ws/'main.c').write_text(source);(ws/'other.py').write_text('print(42)\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'editor.autoLanguageServer':False,'appearance.motion':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get p(){return platformUI},get desktop(){return desktopUI},get dock(){return dock},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.c")');page.wait_for_function('__qa.editor.current==="main.c"')
    def snapshot():return page.evaluate('''()=>[...document.querySelectorAll('.workbench-heading')].filter(n=>n.getBoundingClientRect().width).map(n=>{const r=n.getBoundingClientRect(),actions=[...n.querySelectorAll('.panel-header-actions>[data-header-command]')].filter(b=>b.getBoundingClientRect().width);return {id:n.dataset.panelHeader,height:r.height,inset:getComputedStyle(n).paddingLeft,overflow:n.scrollWidth>n.clientWidth,actions:actions.map(b=>{const a=b.getBoundingClientRect(),g=b.querySelector('svg').getBoundingClientRect();return {command:b.dataset.headerCommand,x:a.x,y:a.y,width:a.width,height:a.height,icon:g.width,right:r.right-a.right}})}})''')
    def aligned():
     stats=snapshot();assert len(stats)==4,stats;assert len(set(n['height'] for n in stats))==1,stats
     for n in stats:
      assert not n['overflow'],n;assert n['inset']=='12px',n;assert [a['command'] for a in n['actions']]==['collapse','detach','more'],n
      assert len(set(a['y'] for a in n['actions']))==1,n
      action_size=32 if page.evaluate('document.documentElement.dataset.density')=='comfortable' else 28
      assert all(a['width']==a['height']==action_size and a['icon']==16 for a in n['actions']),n
      assert abs(n['actions'][-1]['right']-12)<=1,n
     assert len(set(round(n['actions'][0]['y']-page.locator('[data-panel-header='+n['id']+']').bounding_box()['y'],1) for n in stats))==1,stats
     return stats
    for density in ('comfortable','compact'):
     page.evaluate('(v)=>__qa.p.savePreference("appearance.density",v)',density)
     for theme in ('day','dark','forest'):
      page.evaluate('(v)=>__qa.p.savePreference("appearance.theme",v)',theme);matrix.append({'density':density,'theme':theme,'stats':aligned()});page.screenshot(path=str(out/f'{density}-{theme}.png'))
    checks.append('All four panel headers share height, 12px inset, centered density-aware controls, 16px glyphs and collapse/detach/more order in both densities and three themes')
    for id in ('project','console','assistant','editor'):
     control=page.locator('[data-panel-header='+id+'] .panel-header-actions>[data-header-command=more]');control.click();expect(page.locator('#popover')).to_be_visible();assert page.locator('#popover button').count()>0;control.click();expect(page.locator('#popover')).to_be_hidden()
    checks.append('Every More menu opens and closes from the same button and retains pane-specific tools')
    page.locator('[data-panel-header=editor] [data-header-command=more]').click();page.get_by_role('menuitem',name='Espacios guardados',exact=True).click();page.locator('.saved-space-form input').fill('Cabeceras compartidas');page.locator('.saved-space-form button').click();expect(page.locator('.saved-space-list strong')).to_have_text('Cabeceras compartidas');page.keyboard.press('Escape');checks.append('Saved spaces remain accessible through the editor menu and save a real layout in the temporary profile')
    page.locator('[data-panel-header=project] [data-header-command=collapse]').click();assert 'left' in page.evaluate('__qa.dock.state.collapsed');page.locator('[data-dock-expand=left]').click();assert 'left' not in page.evaluate('__qa.dock.state.collapsed')
    page.locator('[data-panel-header=assistant] [data-header-command=collapse]').click();assert 'right' in page.evaluate('__qa.dock.state.collapsed');page.locator('[data-dock-expand=right]').click()
    page.locator('[data-panel-header=console] [data-header-command=collapse]').click();assert 'console' in page.evaluate('__qa.dock.state.hidden');page.evaluate('__qa.dock.show("console")')
    page.locator('[data-panel-header=editor] [data-header-command=collapse]').click();assert page.evaluate('__qa.dock.state.preset')=='focus';page.locator('[data-panel-header=editor] [data-header-command=collapse]').click();assert page.evaluate('__qa.dock.state.preset')!='focus';aligned();checks.append('Project and Melody collapse/restore, terminal hide/show and editor focus/restore preserve the real editor model')
    page.evaluate('__qa.openFile("other.py")');page.locator('.file-tab').filter(has_text='main.c').click();assert page.evaluate('__qa.editor.current')=='main.c';assert page.evaluate('__qa.editor.getValue()')==source
    page.locator('[data-panel-header=console] [data-header-command=more]').click();expect(page.get_by_role('menuitem',name='Limpiar salida',exact=True)).to_be_visible();page.keyboard.press('Escape');checks.append('File tabs remain selectable and terminal secondary tools remain accessible')
    for i in range(7):
     name=f'wide-module-{i}.py';(ws/name).write_text('print(42)\n');page.evaluate('(name)=>__qa.openFile(name)',name)
    for width in (1280,1600,1100,1600):
     page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(120)
     boxes=page.locator('#file-tabs').evaluate('(n)=>({strip:n.getBoundingClientRect().toJSON(),active:n.querySelector(".file-tab.active").getBoundingClientRect().toJSON()})');assert boxes['active']['left']>=boxes['strip']['left']-1 and boxes['active']['right']<=boxes['strip']['right']+1,boxes
    page.evaluate('for(const path of [...__qa.editor.models.keys()])if(path.startsWith("wide-module-"))__qa.editor.close(path);__qa.openFile("main.c")');checks.append('With nine open files, native-size strip changes keep the full active tab visible without switching files or moving editor text')
    page.evaluate('__qa.dock.move("assistant","left")');group=page.locator('#dock-left>.dock-strip');expect(group).to_be_visible()
    for id in ('project','assistant'):
     group.locator('[data-dock-tab='+id+']').click();assert group.locator('.panel-header-actions>[data-header-command]').evaluate_all('(ns)=>ns.map(n=>n.dataset.headerCommand)')==['collapse','detach','more'];group.locator('[data-header-command=more]').click();expect(page.locator('#popover')).to_be_visible();page.keyboard.press('Escape')
    assert group.locator('#ai-cancel-generation').count()==1;group.locator('[data-header-command=more]').click();expect(page.get_by_role('menuitem',name='Nueva conversación',exact=True)).to_be_visible();page.keyboard.press('Escape')
    page.screenshot(path=str(out/'grouped.png'));page.evaluate('__qa.dock.move("assistant","right")');checks.append('Grouped panels retain the same ordered controls and menus follow the selected live pane')
    assert page.locator('[data-panel-header=assistant] .melody-new-chat').is_visible();assert page.locator('#ai-cancel-generation').count()==1
    # Actual browser detach/return path, without native OS or a user session.
    with page.expect_popup() as popup_info:page.locator('[data-panel-header=editor] [data-header-command=detach]').click()
    popup=popup_info.value;popup.wait_for_function('window.lumen?.ready');assert popup.locator('.native-window-heading').is_visible();assert popup.locator('.native-return').is_visible();popup.locator('.native-return').click();page.wait_for_function('!__qa.editor.detachedPaths.has("main.c")');page.wait_for_function('__qa.editor.current==="main.c"');checks.append('The existing detach button opens the real external editor and Return restores its shared buffer')
    page.evaluate('__qa.p.savePreference("general.locale","en")');expect(page.locator('[data-panel-header=project] [data-header-command=more]')).to_have_attribute('aria-label','More options');page.evaluate('__qa.p.savePreference("general.locale","es")')
    for width,height in ((1280,800),(960,540)):
     page.set_viewport_size({'width':width,'height':height});page.evaluate('__qa.dock.show("assistant")');stats=snapshot();assert all(not n['overflow'] for n in stats),stats;assert page.locator('body').evaluate('(n)=>n.scrollWidth<=innerWidth');page.screenshot(path=str(out/f'viewport-{width}.png'))
    checks.append('Labels follow the interface language and narrow logical viewports keep panel controls within bounds')
    assert not errors,errors;assert (ws/'main.c').read_text()==source;assert not app.runner.jobs;checks.append('No browser exceptions, source-file writes or execution processes were introduced');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'matrix':matrix,'errors':errors},ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
