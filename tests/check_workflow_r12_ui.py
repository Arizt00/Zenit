"""Browser regressions against the real backend and Monaco, in a disposable project."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    def passed(label):checks.append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='zenit-workflow-') as tmp:
        base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('def greet(name):\n    return "Hello, " + name\n\nprint(greet("Aurora"))\n');(ws/'other.py').write_text('print(42)\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'en','general.showWelcome':False,'appearance.motion':True,'updates.automatic':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':950})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get dock(){return dock},get platform(){return platformUI},get studio(){return studio},get desktop(){return desktopUI},openFile,perform,openPalette};')
                page.route('**/src/app.js',inject);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.studio.enter()');page.evaluate('__qa.openFile("main.py")')
                page.wait_for_function('__qa.editor.kind==="monaco"&&__qa.editor.current==="main.py"')
                lab=page.locator('.foundation-toggle');page.mouse.move(700,900)
                page.wait_for_function('document.querySelector(".foundation-toggle").getBoundingClientRect().width<42')
                lab.hover();page.wait_for_function('document.querySelector(".foundation-toggle").getBoundingClientRect().width>130');lab.click()
                page.wait_for_selector('[data-lab-section=sessions]');page.wait_for_function('document.querySelector(".foundation-toggle").getBoundingClientRect().width<42')
                passed('Laboratory expands on hover and returns to its icon after opening')
                page.locator('[data-lab-section=sessions]').click();expect(page.locator('.session-create')).to_be_visible()
                gate=threading.Event();started=threading.Event()
                app.features.hilo.submit('QA queue gate',lambda event:(started.set(),gate.wait(30)),workspace=ws)
                assert started.wait(2)
                page.locator('.session-create button[type=submit]').click()
                expect(page.locator('[data-hilo-cancel]')).to_have_count(2)
                queued=next(j for j in app.features.hilo.snapshot()['jobs'] if j['label']=='Lantern · create environment')
                page.locator('[data-hilo-cancel="'+queued['id']+'"]').click()
                assert app.features.hilo.jobs[queued['id']]['event'].is_set()
                gate.set();page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                expect(page.locator('.session-card')).to_have_count(0);passed('Hilo can cancel preparation while the environment form is busy')
                page.locator('.session-create input').fill('Research');page.locator('.session-create button[type=submit]').click()
                expect(page.locator('.session-card')).to_have_count(1,timeout=60000)
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                page.locator('[data-session-action=activate]').click();expect(page.locator('.session-card small')).to_contain_text('Active interpreter')
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                page.locator('.session-save input').fill('research.tern');page.locator('.session-save button').click()
                expect(page.locator('.session-card small')).to_contain_text('research.tern');assert (ws/'research.tern').exists()
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                page.locator('[data-session-action=stop]').click();expect(page.locator('.session-card')).to_have_count(0)
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                page.locator('.session-restore button[type=submit]').click();expect(page.locator('.session-card')).to_have_count(1)
                page.wait_for_function('!document.querySelector(".session-create button[type=submit]").disabled')
                page.locator('.lab-heading').scroll_into_view_if_needed();page.wait_for_timeout(500);page.screenshot(path=str(out/'lantern-environments.png'));passed('Python environment can be created, activated, saved, closed and restored through the UI')
                expect(page.locator('[data-lab-section=connections]')).to_have_count(0)
                page.evaluate('__qa.platform.settings("connections")');expect(page.locator('.connections-grid article')).to_have_count(7);page.wait_for_timeout(750);assert page.locator('[data-setting-category=connections]').get_attribute('aria-current')=='page';page.screenshot(path=str(out/'hilo-connections.png'));passed('Connections exists only in Settings and shows all seven actual application adapters')
                page.locator('#settings-search').fill('font');expect(page.locator('.settings-category:not([hidden])')).to_contain_text('Results')
                page.locator('[data-setting-category=connections]').click();expect(page.locator('.connections-grid')).to_be_visible();expect(page.locator('#settings-search')).to_have_value('')
                page.evaluate('__qa.platform.closePage()')
                page.evaluate('__qa.editor.insertText("# unsaved main\\n",false);__qa.editor.split("main.py","right")')
                page.wait_for_selector('.editor-mount.is-split,#editor-mount.is-split');expect(page.locator('.editor-pane')).to_have_count(2)
                before=page.evaluate('__qa.editor.getValue()')
                page.locator('.editor-pane-heading [data-merge-editor]').last.click();expect(page.locator('.editor-pane')).to_have_count(1);assert page.evaluate('__qa.editor.getValue()')==before
                page.evaluate('__qa.openFile("other.py")');page.evaluate('__qa.editor.insertText("# unsaved other\\n",false);__qa.editor.split("main.py","bottom")')
                mount=page.locator('#editor-mount');box=mount.bounding_box()
                page.locator('[data-pane-document="main.py"]').last.drag_to(mount,target_position={'x':box['width']/2,'y':box['height']/2})
                expect(page.locator('.editor-pane')).to_have_count(1)
                assert '# unsaved other' in page.evaluate('__qa.editor.models.get("other.py").model.getValue()');assert '# unsaved main' in page.evaluate('__qa.editor.models.get("main.py").model.getValue()');passed('Merge button and real drag back to center preserve both unsaved models')
                page.locator('#editor-mount .view-lines').first.click(button='right',position={'x':180,'y':15})
                parent=page.locator('.editor-context-menu').first;parent.get_by_role('menuitem',name='Melody',exact=True).click()
                child=page.locator('.editor-context-menu').nth(1);expect(child).to_be_visible();a=parent.bounding_box();b=child.bounding_box()
                assert abs(b['x']-(a['x']+a['width'])-12)<2 or abs(a['x']-(b['x']+b['width'])-12)<2
                page.keyboard.press('ArrowLeft');expect(page.locator('.editor-context-menu')).to_have_count(1);page.keyboard.press('Escape');passed('Editor submenu has a 12px gap and keyboard navigation returns to its parent')
                page.evaluate('__qa.perform("collapse-left");__qa.perform("collapse-right")');page.wait_for_selector('.dock-slot.is-collapsed');assert page.locator('.dock-slot.is-collapsed').count()==2
                assert all(float(page.locator('.dock-slot.is-collapsed').nth(i).evaluate('(e)=>parseFloat(getComputedStyle(e).borderRadius)'))>=14 for i in range(2));page.screenshot(path=str(out/'collapsed-panels.png'));passed('Both collapsed panels retain rounded corners')
                page.evaluate('__qa.perform("collapse-left");__qa.perform("collapse-right")')
                page.evaluate('__qa.platform.settings("general")');page.wait_for_selector('.settings-content');assert page.locator('.settings-content').evaluate('(e)=>getComputedStyle(e).scrollbarWidth==="none"&&e.scrollWidth<=e.clientWidth+1')
                assert page.locator('.settings-overlay .platform-header').evaluate('(e)=>getComputedStyle(e).borderBottomWidth==="0px"')
                page.wait_for_timeout(750);page.screenshot(path=str(out/'settings.png'));passed('Settings has no top separator or visible scrollbars and no horizontal overflow')
                for theme in ('dark','forest'):
                    page.evaluate('(theme)=>__qa.perform("theme-"+theme)',theme);page.wait_for_timeout(400)
                    assert page.locator('.settings-content').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                    page.screenshot(path=str(out/f'settings-{theme}.png'))
                page.evaluate('__qa.perform("theme-day")');passed('Dark and Forest retain settings geometry without overflow')
                page.evaluate('__qa.platform.closePage();__qa.openPalette()');page.locator('#palette-commands').click();h=page.locator('.command-palette').bounding_box()['height'];page.locator('#palette-files').click();assert abs(page.locator('.command-palette').bounding_box()['height']-h)<1;page.keyboard.press('Escape');passed('Files/commands switching keeps palette geometry stable')
                # Streaming runs against the actual class; it does not force readers to the bottom.
                result=page.evaluate('''async()=>{const {MelodyStream}=await import('/src/melody-stream.js');const scroller=document.createElement('div');scroller.style='position:fixed;top:0;left:0;height:100px;width:240px;overflow:auto';const text=document.createElement('div');text.style='white-space:pre-wrap';scroller.append(text);document.body.append(scroller);const stream=new MelodyStream(text,scroller);stream.update('line\\n'.repeat(200));await new Promise(r=>setTimeout(r,220));scroller.scrollTop=0;scroller.dispatchEvent(new Event('scroll'));stream.update('line\\n'.repeat(220)+'🙂');await new Promise(r=>setTimeout(r,220));stream.finish();const result={same:text.textContent===stream.target,top:scroller.scrollTop};stream.dispose();scroller.remove();return result;}''')
                assert result=={'same':True,'top':0},result;passed('Streaming preserves Unicode and the reading position')
                page.emulate_media(reduced_motion='reduce');lab.hover();assert lab.evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s';passed('Reduced-motion preference disables hover animation')
                assert 'Sesión LSP desconocida' not in page.locator('body').inner_text();assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n')


if __name__=='__main__':main()
