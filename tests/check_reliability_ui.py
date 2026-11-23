"""Real editor recovery and readable evidence on disposable browser profiles."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    out=ROOT/'qa-output/reliability-ui';out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];timings={}
    with tempfile.TemporaryDirectory(prefix='zenit-reliability-ui-') as temporary:
        base=Path(temporary);root=base/'project';root.mkdir()
        source='from helper import VALUE\nprint(VALUE)\n'
        (root/'main.py').write_text(source);(root/'helper.py').write_text('VALUE=7\n')
        original=bytes(range(256))*32;(root/'bytes.bin').write_bytes(original)
        app=Application(ROOT,root,data_dir=base/'profile');f=app.features;app.workspace.trusted=True
        f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'files.autoSave':False,'security.confirmRoutineActions':False})
        f.studio.update({'onboarded':True})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},get desktop(){return desktopUI},get workbench(){return workbenchUI},openFile};')
                page.route('**/src/app.js',inject)
                page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
                timings['first']=page.evaluate('zenitStartup.snapshot()')
                page.evaluate('__qa.openFile("main.py")');page.evaluate('__qa.editor.insertText("# recovered draft\\n",true)')
                draft=page.evaluate('__qa.editor.getValue()')
                page.evaluate('__qa.openFile("bytes.bin")')
                page.locator('[data-binary-offset] input').fill('0x1000');page.locator('[data-binary-offset] button').click()
                page.wait_for_function('__qa.editor.binaryView.item.offset===4096')
                page.locator('[data-binary-edit]').click();page.locator('[data-byte="5"]').click()
                page.locator('[data-binary-edit-form] input').fill('aa');page.locator('[data-binary-edit-form] button').click()
                page.wait_for_function('__qa.editor.models.get("bytes.bin").binaryState.patches.get(4101)?.after===170')
                page.evaluate('__qa.workbench.flush()');page.reload();page.wait_for_function('window.lumen?.ready')
                page.wait_for_function('__qa.editor.models.get("bytes.bin")?.binaryState?.patches.get(4101)?.after===170')
                assert page.evaluate('__qa.editor.models.get("main.py").value')==draft
                assert (root/'bytes.bin').read_bytes()==original and (root/'main.py').read_text()==source
                expect(page.locator('.binary-modified')).to_have_text('1 bytes modificados')
                checks.append('Reload restores unsaved text and pending bytes on another binary page without saving either source')
                page.locator('[data-binary-undo]').click();assert not page.evaluate('__qa.editor.isDirty("bytes.bin")')
                page.locator('[data-binary-redo]').click();assert page.evaluate('__qa.editor.isDirty("bytes.bin")')
                checks.append('Recovered binary changes retain working undo and redo')
                page.evaluate('__qa.workbench.flush()');(root/'bytes.bin').write_bytes(b'converted to plain text')
                page.reload();page.wait_for_function('window.lumen?.ready')
                page.wait_for_function('__qa.editor.models.get("bytes.bin")?.recoveryConflict===true')
                expect(page.locator('[data-binary-save]')).to_be_disabled();expect(page.locator('[data-binary-export]')).to_be_enabled()
                expect(page.locator('.binary-error')).to_contain_text('archivo cambió en disco')
                checks.append('A disk revision conflict preserves recovered bytes for export and disables save')
                page.screenshot(path=str(out/'binary-conflict.png'))
                # Even deletion must not make the next checkpoint forget patches.
                page.evaluate('__qa.workbench.flush()');(root/'bytes.bin').unlink()
                page.reload();page.wait_for_function('window.lumen?.ready')
                page.wait_for_function('__qa.editor.models.get("bytes.bin")?.binaryState?.patches.get(4101)?.after===170')
                expect(page.locator('[data-binary-save]')).to_be_disabled();expect(page.locator('[data-binary-export]')).to_be_enabled()
                page.evaluate('__qa.workbench.flush()')
                assert f.workbenches.snapshot(app.workspace)['session']['documents'][-1]['binary']['patches']
                checks.append('A deleted binary keeps an exportable recovery document through the next checkpoint')
                page.locator('.toast-dismiss').evaluate_all('(buttons)=>buttons.forEach(button=>button.click())')
                page.evaluate('__qa.desktop.handle("performance-report")')
                expect(page.locator('.performance-report')).to_be_visible();expect(page.locator('.performance-report')).to_contain_text('Editor disponible')
                page.wait_for_function('()=>!document.querySelector("#modal")?.getAnimations({subtree:true}).some(a=>a.playState==="running"&&a.effect?.getComputedTiming().iterations!==Infinity)')
                timings['restored']=page.evaluate('zenitStartup.snapshot()')
                page.screenshot(path=str(out/'performance-day.png'))
                page.evaluate('__qa.platform.savePreference("appearance.theme","dark")')
                page.wait_for_function('()=>!document.querySelector("#modal")?.getAnimations({subtree:true}).some(a=>a.playState==="running"&&a.effect?.getComputedTiming().iterations!==Infinity)')
                page.screenshot(path=str(out/'performance-dark.png'))
                page.set_viewport_size({'width':640,'height':720})
                rect=page.locator('.performance-report').bounding_box();assert rect['x']>=0 and rect['x']+rect['width']<=641,rect
                page.screenshot(path=str(out/'performance-640.png'))
                checks.append('Performance report shows measured milestones and shared discovery counters in both themes and fits 640 px')
                page.evaluate('__qa.platform.host.closeModal()');page.set_viewport_size({'width':1600,'height':1000})
                page.evaluate('__qa.openFile("main.py")');page.evaluate('(source)=>{__qa.editor.insertText(source,true);}',source)
                f.lantern.start(app.workspace,'main.py',source,1)
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    state=f.lantern.snapshot()
                    if state.get('code')==0:break
                    time.sleep(.03)
                assert state.get('code')==0,state
                (root/'helper.py').write_text('VALUE=8\n')
                page.evaluate('async()=>{const {showDossier}=await import("/src/experience-r2.js");await showDossier(__qa.platform);}');
                expect(page.locator('.r2-dossier')).to_contain_text('Dependencias modificadas')
                page.locator('.execution-evidence > summary').click()
                expect(page.locator('.execution-evidence')).to_contain_text('helper.py')
                expect(page.locator('.execution-evidence')).to_contain_text('Órdenes registradas')
                page.wait_for_function('()=>!document.querySelector("#modal")?.getAnimations({subtree:true}).some(a=>a.playState==="running"&&a.effect?.getComputedTiming().iterations!==Infinity)')
                page.screenshot(path=str(out/'dossier-dependency-change.png'))
                checks.append('Melody shows changed dependencies despite unchanged main source, with actual target and commands')
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
    result={'checks':checks,'timings':timings,'errors':errors}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'passed':len(checks),'errors':errors}))


if __name__=='__main__':main()
