"""Fresh-profile setup and toolbar regressions, with the real application."""
import argparse
import json
import re
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
    with tempfile.TemporaryDirectory(prefix='zenit-r13-',ignore_cleanup_errors=True) as tmp:
        base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print("Hello")\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        app.features.prefs.update({'general.locale':'es','appearance.motion':True,'updates.automatic':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':950})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get dock(){return dock},get platform(){return platformUI},get studio(){return studio},get desktop(){return desktopUI},openFile,perform};')
                page.route('**/src/app.js',inject);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
                expect(page.locator('#onboarding')).to_be_visible()
                assert page.locator('#app').evaluate('(e)=>e.inert&&getComputedStyle(e).visibility==="hidden"')
                assert page.locator('#onboarding').evaluate('(e)=>getComputedStyle(e).backgroundColor!=="rgba(0, 0, 0, 0)"')
                for theme in ('day','dark','forest'):
                    page.locator(f'[data-choice=theme][data-value={theme}]').click()
                    assert page.locator('#onboarding').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
                    page.screenshot(path=str(out/f'setup-{theme}.png'))
                passed('Fresh setup owns an opaque screen in all three themes; home cannot overlap')
                page.locator('[data-choice=theme][data-value=day]').click();page.locator('#onboard-next').click()
                page.locator('#onboard-name').fill('Alex');page.locator('#onboard-motion').uncheck();page.locator('#onboard-autosave').check()
                expect(page.locator('.preference-label small').first).to_be_visible();page.screenshot(path=str(out/'personalize.png'))
                page.locator('#onboard-back').click();page.locator('#onboard-next').click();expect(page.locator('#onboard-name')).to_have_value('Alex');expect(page.locator('#onboard-motion')).not_to_be_checked();expect(page.locator('#onboard-autosave')).to_be_checked()
                page.locator('#onboard-motion').check();page.locator('#onboard-next').click();page.locator('#onboard-next').click();expect(page.locator('#onboarding')).to_have_count(0)
                page.wait_for_function('!document.documentElement.dataset.screenMotion');expect(page.locator('.welcome-copy')).to_be_visible();assert not page.locator('#app').evaluate('(e)=>e.inert')
                passed('Setup preserves drafts going back, saves preferences and transitions to home')
                page.evaluate('__qa.studio.enter()');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.editor.kind==="monaco"')
                page.mouse.move(600,850)
                for selector in ('.foundation-toggle','.forge-toggle','.debug-button'):
                    button=page.locator(selector);page.wait_for_function('(s)=>document.querySelector(s).getBoundingClientRect().width<42',arg=selector)
                    before=button.bounding_box();search=page.locator('.global-search').bounding_box();button.hover();page.wait_for_timeout(500)
                    after=button.bounding_box();search_after=page.locator('.global-search').bounding_box()
                    assert after['width']>before['width']+40,(selector,before,after)
                    assert abs(after['x']+after['width']-before['x']-before['width'])<2,(selector,before,after)
                    assert search_after['width']<search['width']-40,(selector,search,search_after)
                    page.mouse.move(600,850);page.wait_for_timeout(500)
                lab=page.locator('.foundation-toggle').bounding_box();forge=page.locator('.forge-toggle').bounding_box();assert 7<=forge['x']-lab['x']-lab['width']<=14
                passed('Lab, Forge and Debug expand left with fixed right edges and a fluid search field')
                heading=page.locator('.assistant-heading-title').bounding_box();actions=page.locator('.assistant-heading .heading-actions').bounding_box()
                assert heading['x']+heading['width']<=actions['x']+1 or heading['y']+heading['height']<=actions['y']+1,(heading,actions)
                expect(page.locator('.assistant-heading .heading-actions>[data-panel-float]')).to_be_visible();assert page.locator('[data-panel-float=assistant] svg').get_attribute('data-glyph')=='float'
                page.locator('.assistant-heading-title h2').click();expect(page.locator('#melody-model-picker')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#melody-model-picker')).not_to_be_visible()
                page.screenshot(path=str(out/'workspace.png'));passed('Melody header actions do not overlap; models and floating panel remain accessible')
                page.locator('.foundation-toggle').click();page.locator('[data-lab-section=sessions]').click()
                expect(page.locator('.session-create [name=inherit]')).to_be_visible()
                page.locator('.session-create [name=inherit]').select_option('false')
                page.locator('.session-create input[name=name]').fill('Clean experiment');page.locator('.session-create button[type=submit]').click()
                expect(page.locator('.session-card')).to_have_count(1,timeout=60000);expect(page.locator('.session-card small')).to_contain_text('Python · clean')
                passed('Lantern creates a clean Python environment from its UI')
                def failure(event):raise ValueError('QA: dependency version is unavailable')
                app.features.hilo.submit('Package check',failure,workspace=ws)
                page.locator('[data-hilo-explain]').click(timeout=10000)
                expect(page.locator('#ai-input')).to_have_value(re.compile('QA: dependency version is unavailable'))
                expect(page.locator('#melody-model-picker')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#melody-model-picker')).not_to_be_visible()
                passed('Failed Hilo work can be reviewed by Melody with actual evidence and inline model selection')
                page.evaluate('__qa.studio.onboarding()');page.wait_for_function('!document.documentElement.dataset.screenMotion');expect(page.locator('#onboarding')).to_be_visible()
                page.set_viewport_size({'width':720,'height':700});assert page.locator('#onboarding').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
                page.screenshot(path=str(out/'setup-small.png'));page.locator('#skip-onboarding').click();expect(page.locator('#onboarding')).to_have_count(0)
                page.emulate_media(reduced_motion='reduce');page.evaluate('__qa.studio.onboarding()');page.locator('#skip-onboarding').click();expect(page.locator('#onboarding')).to_have_count(0)
                assert not errors,errors;passed('Reopening setup, small windows, skip and reduced motion complete without JavaScript errors');browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n')

if __name__=='__main__':main()
