"""Window ownership, stable navigation, quiet focus and real dependency surfaces."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    def passed(label):checks.append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='zenit-r14-',ignore_cleanup_errors=True) as tmp:
        base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print("Aurora")\n');(ws/'hello.c').write_text('int main(void) { return 0; }\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'appearance.motion':True,'updates.automatic':False,'security.confirmRoutineActions':False})
        for name in ('nC helpers','Aurora colors','C workspace'):
            package=base/(name+'.vsix')
            with zipfile.ZipFile(package,'w') as archive:archive.writestr('extension/package.json',json.dumps({'name':name.lower().replace(' ','-'),'publisher':'qa','version':'1.0.0','displayName':name,'description':'Tools connected to your workspace. A longer description verifies that metadata and actions retain clear spacing at different window widths.','engines':{'vscode':'*'},'contributes':{}}))
            review=app.features.extensions.inspect_local(str(package));app.features.extensions.install(review['ticket'],True)
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get desktop(){return desktopUI},get preview(){return previewUI},get platform(){return platformUI},get studio(){return studio},openFile,perform};')
                context.route('**/src/app.js',inject);context.on('page',lambda p:p.on('pageerror',lambda e:errors.append(str(e))))
                page=context.new_page();page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.editor.kind==="monaco"')
                page.evaluate('__qa.openFile("hello.c")');page.evaluate('__qa.openFile("main.py")');page.evaluate('(text)=>{__qa.editor.insertText(text,true);__qa.editor.split("hello.c")}', 'print("unsaved")\n')
                with page.expect_popup() as popup:page.evaluate('__qa.desktop.detach("editor","main.py")')
                child=popup.value;child.wait_for_function('window.lumen?.ready');expect(child.locator('.native-editor-shell')).to_be_visible()
                expect(page.locator('[data-tab="main.py"]')).to_have_count(0);expect(page.locator('.editor-pane')).to_have_count(1)
                assert page.evaluate('__qa.editor.current')=='hello.c';assert child.evaluate('__qa.editor.getValue()')=='print("unsaved")\n'
                await_text='print("from external")\n';child.evaluate('(text)=>__qa.editor.insertText(text,true)',await_text)
                page.wait_for_function('__qa.editor.models.get("main.py").model.getValue().includes("from external")')
                page.evaluate('__qa.openFile("main.py")');assert page.evaluate('__qa.editor.current')=='hello.c'
                assert child.locator('.native-window-heading small').inner_text()=='Búfer compartido'
                expect(child.locator('.native-window-heading small')).to_be_visible()
                assert child.locator('.native-window-heading>span>svg').get_attribute('data-glyph')=='editor-window'
                passed('Detached files disappear from tabs and split panes, keep unsaved shared text and cannot reopen in the main window')
                for selector in ('.native-editor-run','.native-editor-terminal','.native-editor-main-terminal'):
                    button=child.locator(selector);child.mouse.move(5,400);child.wait_for_timeout(450);before=button.bounding_box();button.hover();child.wait_for_timeout(480);after=button.bounding_box()
                    assert before['width']<=38 and after['width']>before['width']+45,(selector,before,after)
                    assert abs(before['x']+before['width']-after['x']-after['width'])<2,(selector,before,after)
                child.mouse.move(5,400);child.wait_for_timeout(450);child.screenshot(path=str(out/'external-editor.png'))
                child.locator('.native-editor-terminal').click();expect(child.locator('#terminal-panel')).to_be_visible();child.mouse.move(5,400)
                expect(child.locator('.native-editor-terminal')).to_have_attribute('aria-pressed','true')
                child.locator('.native-return').click();page.wait_for_function('!__qa.editor.detachedPaths.has("main.py")');expect(page.locator('[data-tab="main.py"]')).to_be_visible();assert page.evaluate('__qa.editor.getValue()')==await_text
                assert (ws/'main.py').read_text()=='print("Aurora")\n'
                passed('External actions expand left smoothly; returning restores the latest unsaved text without writing the file')
                with page.expect_popup() as popup:page.evaluate('__qa.preview.newWindow("main.py")')
                first=popup.value;first.wait_for_function('window.lumen?.ready')
                with page.expect_popup() as popup:page.evaluate('__qa.desktop.detach("editor","hello.c")')
                second=popup.value;second.wait_for_function('window.lumen?.ready');expect(page.locator('#file-tabs [data-tab]')).to_have_count(0)
                first.close();page.wait_for_function('!__qa.editor.detachedPaths.has("main.py")');assert page.evaluate('__qa.editor.detachedPaths.has("hello.c")');expect(page.locator('[data-tab="hello.c"]')).to_have_count(0)
                second.close();page.wait_for_function('!__qa.editor.detachedPaths.size');expect(page.locator('#file-tabs [data-tab]')).to_have_count(2)
                passed('All open-in-window routes transfer ownership; closing one of two external editors restores only its own document')
                for width in (1600,1280,900):
                    page.set_viewport_size({'width':width,'height':1000});page.mouse.move(800,60);before=page.locator('.rail-item').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
                    page.locator('.rail-item[data-action=extensions]').click();page.wait_for_timeout(400)
                    after=page.locator('.rail-item').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
                    assert before==after,(width,before,after)
                    page.evaluate('__qa.platform.closePage()')
                passed('Activity buttons keep their positions and sizes when opening Extensions at 1600, 1280 and 900 pixels')
                page.set_viewport_size({'width':1600,'height':1000});page.locator('.rail-item[data-action=extensions]').click();page.wait_for_timeout(30)
                assert page.locator('.rail-item[data-action=extensions] svg').evaluate('(e)=>e.getAnimations().length')>0
                expect(page.locator('.extension-card')).to_have_count(3);page.wait_for_timeout(350);page.screenshot(path=str(out/'extensions.png'))
                for mode in ('cards','compact','list'):
                    page.locator(f'[data-extension-view={mode}]').click();expect(page.locator('#extension-results')).to_have_attribute('data-view',mode);page.wait_for_timeout(350)
                passed('Activity icons animate without layout changes; all extension views remain usable')
                page.locator('[data-extension-mode=native]').click();page.locator('[data-native-language=nc]').click();page.locator('#native-requirement').focus();page.locator('#native-requirement').fill('stoud::io')
                assert page.locator('#native-requirement').evaluate('(e)=>getComputedStyle(e).outlineStyle')=='none'
                assert page.locator('.python-install>div').evaluate('(e)=>getComputedStyle(e).borderColor')=='rgb(115, 129, 152)'
                a=page.locator('.dependency-setup').bounding_box();b=page.locator('.dependency-inventory').bounding_box();assert abs(a['y']-b['y'])<1 and abs(a['height']-b['height'])<1,(a,b)
                page.screenshot(path=str(out/'native-dependencies.png'));page.locator('[data-extension-mode=python]').click();expect(page.locator('.python-environment')).to_be_visible();page.screenshot(path=str(out/'python-dependencies.png'))
                page.set_viewport_size({'width':760,'height':900});assert page.locator('.python-packages').evaluate('(e)=>e.scrollWidth<=e.clientWidth');page.screenshot(path=str(out/'dependencies-small.png'))
                passed('Native and Python package panels share aligned columns, responsive typography and one quiet focus indicator')
                page.set_viewport_size({'width':1600,'height':1000});page.evaluate('__qa.platform.closePage()');page.locator('.foundation-toggle').click();page.locator('[data-lab-section=sessions]').click()
                page.locator('.session-create [name=inherit]').select_option('false');page.locator('.session-create input[name=name]').fill('Scratch environment');page.locator('.session-create button[type=submit]').click();expect(page.locator('.session-card')).to_have_count(1,timeout=60000)
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled');page.locator('[data-session-action=packages]').click();expect(page.locator('.python-environment')).to_contain_text('Scratch environment · Lantern')
                assert '.lumen' in page.locator('.python-environment').inner_text();assert not (ws/'.venv').exists()
                passed('Lantern opens packages in its real active Python environment instead of creating a second .venv')
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n')

if __name__=='__main__':main()
