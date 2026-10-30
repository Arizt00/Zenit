"""Real new-project UI, reviewed C/CMake execution and visible language artifacts."""
import json
from pathlib import Path
import sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    out=ROOT/'qa-output/055-language-projects-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-language-ui-') as folder:
        base=Path(folder);ws=base/'project';ws.mkdir();(ws/'existing.py').write_text('print(42)\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True})
        app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'appearance.motion':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000})
                page.on('pageerror',lambda error:errors.append(str(error)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get desktop(){return desktopUI},get editor(){return editor},get tree(){return tree},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
                page.evaluate('__qa.desktop.handle("project-workflows")');page.locator('[data-task-choice=new]').click()
                expect(page.locator('[data-kit]')).to_have_count(7)
                expected={'c':'include/app.h','cpp':'include/app.hpp','python':'src/zenit_app/__init__.py',
                          'java':'src/main/java/app/Main.java','rust':'src/lib.rs','asm':'include/main.inc'}
                for language,name in expected.items():
                    page.locator('[data-kit="'+language+'"]').click();page.locator('[data-kit-plan="'+language+'"]').click()
                    expect(page.locator('#workflow-review')).to_contain_text(name)
                    assert not (ws/('proyecto-'+language)).exists()
                page.locator('[data-kit=nc]').click();page.locator('[data-kit-plan=nc]').click()
                expect(page.locator('#workflow-review')).to_contain_text('ncc package init')
                checks.append('Seven language choices review their own interfaces and project files without creating them')
                page.locator('[data-kit=c]').click();page.locator('#workflow-kit-folder').fill('structured-c')
                page.locator('[data-kit-plan=c]').click();page.locator('#workflow-create-kit').click()
                page.wait_for_function('document.querySelector("#workflow-review .task-flow-card")?.dataset.state==="success"')
                assert (ws/'structured-c/src/main.c').is_file() and (ws/'structured-c/include/app.h').is_file()
                page.get_by_role('button',name='Abrir archivo de inicio',exact=True).click()
                page.wait_for_function('__qa.editor.current==="structured-c/src/main.c"')
                checks.append('Creating C opens src/main.c and retains its associated include/app.h')
                page.evaluate('__qa.desktop.handle("project-workflows")');page.locator('[data-workflow-action=run]').click()
                expect(page.locator('#workflow-review')).to_contain_text('Carpeta de resultados')
                expect(page.locator('#workflow-review')).to_contain_text('include/app.h')
                page.locator('#workflow-run-plan').click()
                page.wait_for_function('document.querySelector("#workflow-review .task-flow-card")?.dataset.state==="success"',timeout=45000)
                expect(page.locator('#workflow-history')).to_contain_text('42')
                bins=list((ws/'structured-c/build/c').rglob('zenit_app.exe' if sys.platform=='win32' else 'zenit_app'))
                assert bins
                tree=page.evaluate('__qa.tree')
                assert str(bins[0].relative_to(ws)).replace('\\','/') in json.dumps(tree)
                assert not any('/build/' in path for path in app.workspace.files())
                checks.append('Real CMake/Ninja build runs and the Explorer shows its executable; generated files stay out of source inventories')
                page.screenshot(path=str(out/'review-and-results.png'))
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(checks),'errors':errors},ensure_ascii=False))


if __name__=='__main__':main()
