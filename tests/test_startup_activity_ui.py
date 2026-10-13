"""Boot recovery and real activity interactions, using a disposable QA project."""
import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];metrics={}
    def passed(name):
        checks.append(name);print('PASS',name,flush=True)
    with tempfile.TemporaryDirectory(prefix='zenit-startup-ui-') as tmp:
        ws=Path(tmp)/'project';ws.mkdir();(ws/'src').mkdir()
        for name,source in [('src/Example.java','public class Example { int value = 42; }'),('main.py','print(42)'),('package.json','{}')]:
            (ws/name).write_text(source,encoding='utf-8')
        app=Application(ROOT,ws,data_dir=Path(tmp)/'profile')
        app.features.studio.update({'onboarded':True,'displayName':'Perfil de prueba'})
        app.features.prefs.update({'general.locale':'es','updates.automatic':False,'appearance.motion':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1672,'height':941})
                page.on('pageerror',lambda e:errors.append(str(e)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get dock(){return dock},get studio(){return studio},get platform(){return platformUI},get editor(){return editor},openFile};')
                page.route('**/src/app.js',inject)
                page.goto(base);page.wait_for_function('window.lumen?.ready')
                metrics['browserBoot']=page.evaluate('zenitStartup.snapshot()')
                assert metrics['browserBoot']['complete'] and not metrics['browserBoot']['failed']
                expect(page.locator('#startup-screen')).to_be_hidden()
                passed('Browser boot finishes with real Monaco and no desktop wait')
                page.wait_for_selector('.welcome-scene .gpu-ready')
                page.screenshot(path=str(args.output/'welcome-day.png'))
                canvas=page.evaluate('window.__welcome=document.querySelector("canvas[data-glass=welcome]");__welcome.dataset.geometry')
                assert canvas=='blender-double-wall'
                page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","dark")')
                metrics['welcomeStyles']=page.evaluate('''() => Object.fromEntries(['.welcome-copy h1','.welcome-copy p','.welcome-profile','.welcome-footer','.welcome-scene'].map(selector=>{const node=document.querySelector(selector),s=getComputedStyle(node),r=node.getBoundingClientRect();return [selector,{size:s.fontSize,color:s.color,line:s.lineHeight,rect:{x:r.x,y:r.y,width:r.width,height:r.height}}]}))''')
                page.screenshot(path=str(args.output/'welcome-dark.png'))
                assert page.evaluate('__welcome===document.querySelector("canvas[data-glass=welcome]")')
                passed('Day and dark welcome retain the real Blender/Babylon canvas')
                fresh=browser.new_context();first=fresh.new_page()
                first.route('**/src/app.js',lambda route:route.fulfill(status=200,content_type='text/javascript',body=''))
                first.goto(base);assert first.evaluate('document.documentElement.dataset.theme')=='dark'
                assert first.evaluate('localStorage.length')==0
                first.close();fresh.close();passed('A fresh browser origin receives the actual profile theme before the app module runs')
                page.evaluate('async()=>{await __qa.openFile("src/Example.java");await __qa.openFile("main.py");await __qa.studio.save({recent:[{path:"src/Example.java",workspace:'+json.dumps(str(ws))+',openedAt:new Date().toISOString()},{path:"main.py",workspace:'+json.dumps(str(ws))+',openedAt:new Date(Date.now()-86400000).toISOString()},{path:"package.json",workspace:'+json.dumps(str(ws))+',openedAt:new Date(Date.now()-86400000).toISOString()}]});__qa.studio.showActivity();}')
                page.screenshot(path=str(args.output/'activity-dark.png'))
                page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","day")')
                page.screenshot(path=str(args.output/'activity-day.png'))
                assert page.evaluate('()=>{const list=document.querySelector(".profile-activity-list").getBoundingClientRect(),rows=[...document.querySelectorAll(".activity-row")];return rows.every(row=>row.getBoundingClientRect().bottom<=list.bottom+1)}')
                assert page.evaluate('()=>document.querySelector(".activity-footer").getBoundingClientRect().bottom<=document.querySelector(".activity-profile").getBoundingClientRect().bottom')
                page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","dark")')
                expect(page.locator('.profile-activity-file')).to_have_count(3)
                page.keyboard.press('Control+f');page.locator('.activity-search input').fill('main')
                expect(page.locator('.profile-activity-file')).to_have_count(1)
                page.keyboard.press('Escape');page.evaluate('__qa.studio.showActivity()')
                expect(page.locator('.activity-search input')).to_have_value('main')
                passed('Activity preserves a real history filter after closing and reopening')
                page.locator('.activity-clear').click();expect(page.locator('.profile-activity-file')).to_have_count(3)
                page.keyboard.press('ArrowDown');expect(page.locator('.profile-activity-file').first).to_be_focused()
                page.keyboard.press('ArrowDown');expect(page.locator('.profile-activity-file').nth(1)).to_be_focused()
                page.keyboard.press('Enter');page.wait_for_function('__qa.editor.current==="main.py"')
                passed('Clear search, arrows and Enter reopen an actual buffer')
                page.evaluate('__qa.studio.showActivity()')
                latest=page.evaluate('__qa.studio.profile.recent.toSorted((a,b)=>new Date(b.openedAt)-new Date(a.openedAt))[0].path')
                page.locator('.activity-resume').click()
                page.wait_for_function('(path)=>__qa.editor.current===path',arg=latest.replace('\\','/'))
                passed('Continue opens the actual most recent file')
                page.evaluate('__qa.studio.showActivity()');page.locator('[data-activity-tab=projects]').click()
                expect(page.locator('[data-activity-project]')).to_have_count(1)
                page.keyboard.press('Escape');page.evaluate('__qa.studio.showActivity()')
                expect(page.locator('[data-activity-tab=projects]')).to_have_attribute('aria-selected','true')
                passed('Activity projects and selected tab survive reopening')
                page.locator('[data-activity-tab=files]').click()
                page.locator('.activity-row-menu').first.click();expect(page.locator('#popover')).to_be_visible()
                page.keyboard.press('Escape');expect(page.locator('#modal')).to_be_visible();expect(page.locator('#popover')).to_be_hidden()
                page.locator('.activity-row-menu').first.click();page.keyboard.press('Tab');expect(page.locator('#modal')).to_be_visible();expect(page.locator('#popover')).to_be_hidden()
                passed('Activity row menus open above the sheet and Escape retains the sheet')
                page.evaluate('async()=>{const c=document.createElement("canvas");c.width=c.height=64;const x=c.getContext("2d");x.fillStyle="#d798aa";x.fillRect(0,0,64,64);x.fillStyle="#80bde5";x.fillRect(0,0,32,64);await __qa.studio.save({avatar:c.toDataURL("image/png")});__qa.studio.showActivity();}')
                assert page.locator('.activity-cover img').get_attribute('src')==page.locator('.activity-avatar img').get_attribute('src')
                assert page.locator('.activity-cover img').evaluate('e=>Number(getComputedStyle(e).opacity)<.3')
                page.screenshot(path=str(args.output/'activity-photo.png'));passed('The faded cover uses exactly the actual local profile image')
                page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","day")')
                page.screenshot(path=str(args.output/'activity-photo-day.png'))
                page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","dark")')
                page.evaluate('async()=>{await __qa.studio.save({avatar:""});__qa.studio.showActivity();}')
                for width,height in [(1280,720),(1366,768),(1920,1080),(640,360)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    box=page.locator('#modal').bounding_box();assert box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+.5 and box['y']+box['height']<=height+.5,box
                    page.screenshot(path=str(args.output/f'activity-{width}x{height}.png'))
                passed('Activity stays inside four desktop and compact viewports')
                assert page.locator('.profile-activity-list').evaluate('e=>getComputedStyle(e).scrollbarWidth')=='none'
                page.locator('.profile-activity-list').hover();page.mouse.wheel(0,160)
                page.wait_for_function('document.querySelector(".profile-activity-list").scrollTop>0')
                page.screenshot(path=str(args.output/'scrollbar-hidden.png'));passed('Scrollbars are invisible while real mouse-wheel scrolling still works')
                page.set_viewport_size({'width':1672,'height':941});page.keyboard.press('Escape')
                page.evaluate('__qa.dock.nativeDetached.add("project");__qa.dock.hide("project")')
                page.wait_for_function('JSON.stringify(__qa.studio.profile.layout)===JSON.stringify(__qa.dock.snapshot({persistent:true}))')
                page.evaluate('async()=>await __qa.studio.queue')
                assert not app.features.studio.export()['layout']['hidden']
                page.evaluate('__qa.dock.nativeDetached.delete("project");__qa.dock.show("project")')
                page.wait_for_function('JSON.stringify(__qa.studio.profile.layout)===JSON.stringify(__qa.dock.snapshot({persistent:true}))')
                page.evaluate('async()=>await __qa.studio.queue')
                saved=app.features.studio.export()['layout']
                child=browser.new_page(viewport={'width':900,'height':600});child.goto(base+'?panel=project');child.wait_for_function('window.lumen?.ready');child.set_viewport_size({'width':800,'height':550});child.close()
                assert app.features.studio.export()['layout']==saved
                passed('Native detach visibility and auxiliary resizing cannot overwrite the saved main layout')
                page.route('**/src/studio.js',lambda route:route.fulfill(status=404,body='Module unavailable'))
                page.reload();expect(page.locator('#connection-overlay')).to_be_visible()
                expect(page.locator('#connection-overlay')).to_contain_text('módulo')
                assert not page.evaluate('window.lumen?.ready||false')
                page.screenshot(path=str(args.output/'startup-missing-module.png'))
                page.unroute('**/src/studio.js');page.locator('#retry-connection').click()
                try:page.wait_for_function('window.lumen?.ready',timeout=30000)
                except Exception:
                    (args.output/'retry-failure.json').write_text(json.dumps(page.evaluate('()=>({boot:zenitStartup.snapshot(),ready:window.lumen?.ready,errors:[...document.querySelectorAll(".error-message,.toast,#connection-overlay")].map(e=>e.textContent),monaco:typeof monaco})'),indent=2),encoding='utf-8')
                    raise
                passed('A failed module import is visible and Retry recovers the actual app')
                assert not errors,errors
                passed('Normal interactions produce no uncaught JavaScript errors')
                browser.close()
        finally:
            server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (args.output/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'metrics':metrics,'fixture':'Disposable Java/Python/JSON files and real Babylon/Monaco. Deliberate 404 tests error recovery; no user profile or model requests.'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
