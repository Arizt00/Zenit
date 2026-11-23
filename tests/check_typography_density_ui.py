"""Real workbench geometry, preferences and browser device-scale emulation.

This does not change Windows display settings or certify native DPI switching.
"""
import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/typography';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];matrix=[]
 with tempfile.TemporaryDirectory(prefix='zenit-typography-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();source='int main(void) {\n    int value = 42;\n    return value;\n}\n';(ws/'main.c').write_text(source)
  app=Application(ROOT,ws,data_dir=base/'profile');app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'editor.autoLanguageServer':False,'appearance.density':'compact','appearance.motion':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True)
    def prepare(context):
     page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
     def inject(route):
      response=route.fetch();route.fulfill(response=response,body='window.__densityAtBootstrap=document.documentElement.dataset.density;\n'+response.text()+'\nwindow.__qa={get editor(){return editor},get p(){return platformUI},get desktop(){return desktopUI},openFile};')
     page.route('**/src/app.js',inject);response=page.goto(f'http://127.0.0.1:{server.server_port}');assert 'data-density="'+app.features.prefs.get('appearance.density')+'"' in response.text();page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.c")');page.wait_for_function('__qa.editor.current==="main.c"');return page
    def font(page,selector):return page.locator(selector).first.evaluate('(n)=>getComputedStyle(n).fontSize')
    def snapshot(page):return page.evaluate('''()=>{const size=s=>getComputedStyle(document.querySelector(s)).fontSize,box=s=>document.querySelector(s).getBoundingClientRect(),headers=['#project-panel>.panel-heading','.editor-tabbar','#assistant-panel>.assistant-heading'].map(s=>box(s)).filter(r=>r.width>0);return {density:document.documentElement.dataset.density,title:size('.project-workflow-heading h3'),body:size('[data-workflow-action=run]'),description:size('.project-workflow-heading p'),metadata:size('.project-subtle'),row:box('.tree-row').height,button:box('[data-workflow-action=run]').height,headers:headers.map(r=>({y:r.y,height:r.height})),editor:__qa.editor.view.getOption(monaco.editor.EditorOption.fontInfo).fontSize,code:__qa.editor.getValue(),overflow:document.querySelector('.project-workflows').scrollWidth>document.querySelector('.project-workflows').clientWidth}}''')
    def aligned(stats):
     assert not stats['overflow'],stats
     assert len(set(round(r['y'],1) for r in stats['headers']))==1,stats
     assert len(set(round(r['height'],1) for r in stats['headers']))==1,stats
     assert [stats[k] for k in ('title','body','description','metadata')]==['18px','13px','12px','11px'],stats
    context=browser.new_context(viewport={'width':1600,'height':1000});page=prepare(context);assert page.evaluate('__densityAtBootstrap')=='compact';checks.append('Saved density is present in the HTML and respected before application bootstrap')
    page.evaluate('__qa.desktop.handle("project-workflows")');compact=snapshot(page);aligned(compact)
    page.evaluate('__qa.p.settings("appearance")');density=page.get_by_role('combobox',name='Densidad',exact=True);density.wait_for();assert density.get_attribute('aria-describedby')=='pref-appearance-density-hint';density.click();page.get_by_role('option',name='Cómoda',exact=True).click();page.wait_for_function('document.documentElement.dataset.density==="comfortable"');page.evaluate('__qa.p.settingsWrite');assert app.features.prefs.get('appearance.density')=='comfortable';expect(page.locator('[data-density-value]')).to_have_text('Cómoda')
    sizes=[font(page,'.density-sample-'+role) for role in ('title','body','description','metadata')];assert sizes==['18px','13px','12px','11px'],sizes;page.locator('.density-preview').scroll_into_view_if_needed();page.screenshot(path=str(out/'settings-comfortable.png'));checks.append('Appearance changes density through the real listbox, with an accessible hint and live four-level preview')
    page.evaluate('__qa.desktop.handle("project-workflows")');comfortable=snapshot(page);aligned(comfortable);assert compact['row']<comfortable['row'] and compact['button']<comfortable['button'];assert compact['editor']==comfortable['editor'] and compact['code']==comfortable['code']==source;matrix.extend([comfortable,compact]);page.screenshot(path=str(out/'project-comfortable.png'));checks.append('Density changes spacing, row heights and all aligned panel headers while preserving UI text size, editor font and source')
    titles=[comfortable['title']];page.evaluate('__qa.desktop.handle("foundation")');titles.append(font(page,'.lab-heading h2'));page.locator('#lab-tab-sdk').click();page.locator('.sdk-manager h3').wait_for();titles.append(font(page,'.sdk-manager h3'));page.locator('#lab-tab-machines').click();page.locator('.machine-library h3').first.wait_for();titles.append(font(page,'.machine-library h3'));page.evaluate('__qa.p.extensions("native")');page.locator('.native-packages h3').wait_for();titles.append(font(page,'.native-packages h3'));assert set(titles)=={'18px'},titles;assert page.locator('.python-heading .platform-eyebrow').inner_text()=='Dependencias nativas';assert page.locator('.python-heading .platform-eyebrow').evaluate('(n)=>getComputedStyle(n).letterSpacing')=='normal' or page.locator('.python-heading .platform-eyebrow').evaluate('(n)=>getComputedStyle(n).letterSpacing')=='0px';checks.append('Project, Laboratory, SDK, machines and native dependencies use the same panel-title scale and sentence-case captions')
    for theme in ('day','dark','forest'):
     page.evaluate('(theme)=>__qa.p.savePreference("appearance.theme",theme)',theme);page.evaluate('__qa.desktop.handle("project-workflows")');aligned(snapshot(page));page.screenshot(path=str(out/('project-'+theme+'.png')))
    page.evaluate('__qa.p.savePreference("appearance.density","compact")');page.reload();page.wait_for_function('window.lumen?.ready');assert page.evaluate('__densityAtBootstrap')=='compact';assert page.evaluate('document.documentElement.dataset.density')=='compact';page.evaluate('__qa.openFile("main.c")');page.evaluate('__qa.desktop.handle("project-workflows")');aligned(snapshot(page));page.screenshot(path=str(out/'project-compact.png'));checks.append('Three themes retain the same typography; compact density survives reload without reverting to comfortable at bootstrap')
    page.evaluate('__qa.p.savePreference("general.locale","en")');page.evaluate('__qa.p.settings("appearance")');expect(page.locator('[data-density-value]')).to_have_text('Compact');expect(page.locator('.density-sample-title')).to_have_text('Project');checks.append('Density controls and preview follow the interface language')
    page.evaluate('__qa.p.savePreference("general.locale","es")');page.evaluate('__qa.p.closePage()');page.evaluate('document.documentElement.style.fontSize="20px"');page.evaluate('__qa.desktop.handle("project-workflows")');assert font(page,'.project-workflow-heading h3')=='22.5px';assert font(page,'[data-workflow-action=run]')=='16.25px';assert not page.locator('.project-workflows').evaluate('(n)=>n.scrollWidth>n.clientWidth');page.screenshot(path=str(out/'relative-text-size.png'));checks.append('Relative text units enlarge with the root text size without horizontal overflow or changing the code font');context.close()
    for scale in (1,1.25,1.5,2):
     context=browser.new_context(viewport={'width':round(1920/scale),'height':round(1080/scale)},device_scale_factor=scale);page=prepare(context);assert page.evaluate('devicePixelRatio')==scale
     for density_value in ('comfortable','compact'):
      page.evaluate('(density)=>__qa.p.savePreference("appearance.density",density)',density_value);page.evaluate('__qa.desktop.handle("project-workflows")');stats=snapshot(page);aligned(stats);assert page.locator('body').evaluate('(n)=>n.scrollWidth<=innerWidth');rail=page.locator('.activity-rail').evaluate('(n)=>({top:n.getBoundingClientRect().top,bottom:n.getBoundingClientRect().bottom,buttons:[...n.querySelectorAll(".rail-item")].filter(b=>b.getBoundingClientRect().width).map(b=>({label:b.textContent.trim(),bottom:b.getBoundingClientRect().bottom}))})');assert all(b['bottom']<=rail['bottom']+1 for b in rail['buttons']),rail;page.screenshot(path=str(out/f'scale-{scale}-{density_value}.png'),scale='device');matrix.append({'scale':scale,'cssViewport':[round(1920/scale),round(1080/scale)],'rail':rail,**stats})
      page.evaluate('__qa.p.settings("appearance")');combo=page.get_by_role('combobox',name='Densidad',exact=True);combo.click();option=page.get_by_role('option',name='Compacta' if density_value=='comfortable' else 'Cómoda',exact=True);option.wait_for();rect=page.locator('#lumen-options').bounding_box();assert rect['x']>=0 and rect['y']>=0 and rect['x']+rect['width']<=page.viewport_size['width']+1 and rect['y']+rect['height']<=page.viewport_size['height']+1,rect;page.keyboard.press('Escape');page.keyboard.press('Escape')
     context.close()
    checks.append('Both densities fit logical viewports at 100%, 125%, 150% and 200% device scale; settings listboxes stay within the window')
    assert not errors,errors;assert (ws/'main.c').read_text()==source;assert not app.runner.jobs;checks.append('No browser exceptions, source changes or execution processes were introduced by typography or density controls');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'matrix':matrix,'errors':errors,'method':'Edge device-scale emulation, not a native Windows DPI switch.'},ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
