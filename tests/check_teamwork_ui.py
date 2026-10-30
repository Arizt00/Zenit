"""Visual acceptance on isolated fixtures; never touches the installed profile."""
import hashlib,json,sys,tempfile,threading,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def until(predicate,seconds=25):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.05)
    raise AssertionError('Fixture preparation did not finish')

def main():
    out=ROOT/'qa-output/teamwork-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-teamwork-ui-',ignore_cleanup_errors=True) as folder:
        base=Path(folder);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('print(42)\n');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
        live=app.features.lantern;live.start(app.workspace,'main.py','print(42)\n',1)
        until(lambda:live.job and live.job.done and live.revision==1)
        assert len(live.snapshot()['history'])==1
        live.buffer(app.workspace,'main.py','print(0)\n',2);until(lambda:live.job and live.job.done and live.revision==2)
        assert len(live.snapshot()['history'])==2
        live.buffer(app.workspace,'main.py','print(42)\n',3);until(lambda:live.job and live.job.done and live.revision==3);live.stop()
        assert all(r['replayAvailable'] for r in live.history) and len(live.history)==3
        python=app.features.python_packages.base();inventory=app.features.tern.portability.inventory(python)
        data={'schema':2,'type':'zenit-environment','kind':'python','name':'Reviewed reconstruction','target':{'kind':'local'},'platform':{'system':inventory['system'],'machine':inventory['machine']},'tools':[{'name':'python','version':inventory['version'],'implementation':inventory['implementation']}],'dependencies':[],'artifacts':[],'preparation':[{'action':'python.venv'},{'action':'python.install-locked'}]}
        with zipfile.ZipFile(ws/'reviewed.tern.zip','w') as archive:archive.writestr('environment.tern',json.dumps(data))
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('response',lambda response:print('HTTP FAILURE',response.url,response.text(),flush=True) if response.status>=400 and '/api/' in response.url else None)
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get studio(){return studio},get editor(){return editor},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.editor.current==="main.py"')
                page.locator('[data-lantern=rules]').click();page.get_by_role('button',name='Localizar primer cambio').click();expect(page.locator('.lantern-regression-form [name=revision]')).to_have_count(3);page.get_by_role('button',name='Revisar investigación',exact=True).click();expect(page.locator('[data-regression-run]')).to_be_visible();page.screenshot(path=str(out/'regression-review.png'));page.locator('[data-regression-run]').click();expect(page.locator('.lantern-regression-result')).to_contain_text('resultado distinto: r2',timeout=60000);expect(page.locator('.lantern-regression-result')).to_contain_text('6 ensayos');page.screenshot(path=str(out/'first-changed-revision.png'));checks.append('Actual Lantern captures three bounded source snapshots; reviewed UI replays six sequential trials and finds r2 despite r3 recovering')
                page.locator('[data-regression-melody]').click();expect(page.locator('#ai-input')).to_have_value(__import__('re').compile('Analiza esta investigación'));assert 'firstChangedRevision' in page.locator('#ai-input').input_value();checks.append('Investigation prepares a factual Melody prompt without sending it or detaching the assistant')
                page.locator('[data-lantern=rules]').click();page.get_by_role('button',name='Reducir entrada fallida').click();expect(page.locator('.lantern-regression-form')).to_be_visible();page.locator('.lantern-regression-form [name=stdin]').fill('irrelevant ! text');page.locator('.lantern-regression-form [name=expectedOutput]').fill('OK\n')
                source='import sys\ntext=sys.stdin.read()\nprint("BUG" if "!" in text else "OK")\n'
                # Reopen from the actual editor buffer; source remains unsaved.
                page.evaluate('(s)=>__qa.editor.view.getModel().setValue(s)',source);page.evaluate('__qa.platform.host.closeModal()');page.locator('[data-lantern=rules]').click();page.get_by_role('button',name='Reducir entrada fallida').click();expect(page.locator('.lantern-regression-form')).to_be_visible();page.locator('.lantern-regression-form [name=stdin]').fill('irrelevant ! text');page.locator('.lantern-regression-form [name=expectedOutput]').fill('OK\n');page.get_by_role('button',name='Revisar investigación',exact=True).click();page.locator('[data-regression-run]').click();expect(page.locator('.lantern-regression-result')).to_be_visible(timeout=60000);expect(page.locator('.lantern-regression-result pre').first).to_contain_text('!');assert (ws/'main.py').read_text()=='print(42)\n';page.screenshot(path=str(out/'reduced-input.png'));checks.append('Input reducer runs the reviewed unsaved buffer, preserves the failure and leaves the saved project intact')
                page.evaluate('__qa.platform.host.closeModal()');page.locator('.development-tools').click();page.get_by_role('menuitem',name='Laboratorio',exact=True).click();page.locator('[data-lab-section=sessions]').click();expect(page.locator('.tern-portability')).to_be_visible();page.locator('[data-tern-import] select').select_option('reviewed.tern.zip');page.locator('[data-tern-inspect]').click();expect(page.locator('[data-tern-rebuild]')).to_be_enabled(timeout=45000);expect(page.locator('.tern-portability-report')).to_contain_text('SHA-256');page.screenshot(path=str(out/'environment-reviewed.png'))
                page.locator('[data-tern-rebuild]').click();expect(page.locator('.tern-portability-report')).to_contain_text('Entorno reconstruido sin red',timeout=90000);assert len(app.features.tern.sessions)==1;identity=next(iter(app.features.tern.sessions));receipt=app.features.tern.directory(app.workspace,identity)/'reconstruction.json';assert json.loads(receipt.read_text())['bundleSha256']==hashlib.sha256((ws/'reviewed.tern.zip').read_bytes()).hexdigest();page.screenshot(path=str(out/'environment-reconstructed.png'));checks.append('Portability UI binds rebuild to the reviewed SHA-256 and creates an independent Python environment with a reconstruction receipt')
                assert not errors,errors;context.close();browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'scope':'One Windows station, disposable project and profile; real tools and browser UI.'},ensure_ascii=False,indent=2),encoding='utf-8')
    for check in checks:print('PASS',check,flush=True)

if __name__=='__main__':main()
