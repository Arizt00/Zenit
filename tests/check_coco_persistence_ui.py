"""Recovery controls exercised against a recreated backend and real jobs."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    out=ROOT/'qa-output/coco-persistence-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-coco-persistence-ui-',ignore_cleanup_errors=True) as directory:
        base=Path(directory);workspace=base/'project';workspace.mkdir();profile=base/'profile'
        (workspace/'main.py').write_text('print("RECOVERED_RESULT")\n',encoding='utf-8')
        (workspace/'worker.py').write_text('import time\nprint("PARTIAL",flush=True)\ntime.sleep(30)\n',encoding='utf-8')
        original=Application(ROOT,workspace,data_dir=profile);original.workspace.trusted=True
        original.features.studio.update({'onboarded':True});original.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
        team=original.features.team;state=team.start(original.workspace,{'protocol':2,'shareProject':True,'allowRun':True,'documents':[{'path':'main.py'},{'path':'worker.py'}]})
        finished=team.request({'action':'run','path':'main.py','requestId':'completed'})
        deadline=time.monotonic()+12
        while not original.runner.jobs[finished['job']].done and time.monotonic()<deadline:time.sleep(.02)
        assert original.runner.jobs[finished['job']].code==0
        team.request({'action':'job','job':finished['job']})
        pending=team.request({'action':'run','path':'worker.py','requestId':'interrupted'})
        deadline=time.monotonic()+8
        while 'PARTIAL' not in original.runner.jobs[pending['job']].output and time.monotonic()<deadline:time.sleep(.02)
        original.features.shutdown()
        (workspace/'main.py').write_text('print("EXTERNAL_CHANGE")\n',encoding='utf-8')
        app=Application(ROOT,workspace,data_dir=profile);app.workspace.trusted=True
        assert app.features.team.room is None and app.features.team.server is None
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get team(){return teamUI},get editor(){return editor},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
                page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.editor.current==="main.py"');page.evaluate('__qa.editor.view.getModel().setValue("print(\\"LOCAL_PENDING_TEXT\\")\\n")')
                page.get_by_role('button',name='Co-Code',exact=True).click();expect(page.get_by_role('button',name='Continuar sesión',exact=True)).to_be_visible()
                assert app.features.team.server is None;page.wait_for_timeout(350);page.screenshot(path=str(out/'recovery-ready.png'));checks.append('Recovery is offered without opening a listener or restarting programs')
                page.get_by_role('button',name='Continuar sesión',exact=True).click();expect(page.locator('[data-coco-recovered]')).to_contain_text('requiere atención')
                page.wait_for_function('window.__qa.team?.files.size===2');assert app.features.team.room.id==state['room'];assert not app.runner.jobs
                expect(page.locator('[data-coco-recovered]')).to_contain_text('main.py');expect(page.locator('[data-coco-recovered]')).to_contain_text('worker.py')
                assert 'RECOVERED_RESULT' in page.evaluate('__qa.editor.getValue()');assert (workspace/'main.py').read_text(encoding='utf-8')=='print("EXTERNAL_CHANGE")\n'
                page.wait_for_timeout(350);assert page.locator('#modal').evaluate('(n)=>n.scrollTop')==0;page.screenshot(path=str(out/'recovered-attention.png'));checks.append('Recovered shared text stays separate from externally changed disk content; interrupted job is visible')
                page.get_by_role('button',name='Revisar borrador · main.py',exact=True).click();expect(page.locator('.coco-local-draft pre')).to_contain_text('LOCAL_PENDING_TEXT')
                assert len(app.features.team.store.local_drafts(workspace))==1;page.get_by_role('button',name='Volver a CoCo',exact=True).click();checks.append('A different recovered local draft is stored separately before synchronization replaces the editor text')
                page.get_by_role('button',name='Confirmar interrupción',exact=True).click();expect(page.get_by_role('button',name='Confirmar interrupción',exact=True)).to_have_count(0)
                assert not app.runner.jobs;checks.append('Host acknowledges an interruption without spawning a replacement process')
                page.locator('[data-team-origin]').click();expect(page.locator('.team-evidence')).to_contain_text('cambiaron después de iniciar')
                page.screenshot(path=str(out/'recovered-evidence.png'));checks.append('Execution provenance survives restart and marks changed source as stale')
                page.get_by_role('button',name='Volver a CoCo',exact=True).click()
                for width,height in ((1600,1000),(800,600),(640,600)):
                    page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(180)
                    assert page.locator('.coco-recovery').evaluate_all('(nodes)=>nodes.filter(n=>!n.hidden).every(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth;})')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.screenshot(path=str(out/f'recovery-{width}.png'))
                checks.append('Recovery panels fit at 1600, 800 and 640 pixels without horizontal overflow')
                assert not errors,errors;context.close();browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown()
    report={'checks':checks,'errors':errors,'scope':'Disposable profiles on one Windows station; real programs and a recreated backend.'}
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for check in checks:print('PASS',check,flush=True)


if __name__=='__main__':main()
