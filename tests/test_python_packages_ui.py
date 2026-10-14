"""The Extensions Python tab installs a real offline wheel with real pip."""
import argparse,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.server import Application,LumenServer
from test_python_packages import wheel,wait_job
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-python-ui-') as tmp:
        root=Path(tmp);ws=root/'Aurora';ws.mkdir();(ws/'main.py').write_text('from zenit_qa_package import VALUE\nprint(VALUE)\n');wheel(ws)
        app=Application(ROOT,ws,data_dir=root/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'en','general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'security.confirmRoutineActions':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1672,'height':1000})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get p(){return platformUI},openFile};')
                page.route('**/src/app.js',inject);page.on('pageerror',lambda e:errors.append(e.message));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")');page.locator('[data-action=extensions].rail-item').click();page.locator('[data-extension-mode=python]').click()
                expect(page.locator('.python-environment')).to_contain_text('Bundled');expect(page.locator('.python-environment')).to_contain_text('Installing will prepare .venv');assert page.evaluate('document.querySelector("#assistant-panel").getBoundingClientRect().width===0||getComputedStyle(document.querySelector("#assistant-panel")).display==="none"');checks.append('Extensions opens the Python package manager in its dedicated work surface')
                page.locator('[data-python-scope=base]').click();expect(page.locator('.python-package-list')).to_contain_text('numpy');page.locator('.python-list-toolbar input').fill('pytest');expect(page.locator('.python-package-list article')).to_have_count(1);page.locator('.python-list-toolbar input').fill('');page.locator('[data-python-scope=project]').click();checks.append('The bundled package inventory and filtering show actual installed distribution metadata')
                page.locator('[data-python-action=requirements]').click();page.wait_for_function('__qa.p.pythonPackages.data?.task?.done===true',timeout=60000);assert page.evaluate('__qa.p.pythonPackages.data.task.code')==0;expect(page.locator('.python-package-list')).to_contain_text('zenit-qa-package');expect(page.locator('.python-package-list')).to_contain_text('1.0.0');expect(page.locator('.python-task')).to_contain_text('Completed');checks.append('Install requirements creates .venv and installs the declared offline wheel through actual pip with visible output')
                plan=app.features.runtimes.plan(app.workspace,'main.py');job=wait_job(app,app.runner.start(plan['commands'],ws));assert 'actual wheel 1.0.0' in job.output;checks.append('The normal Python run plan imports the package from the environment prepared in Extensions')
                page.screenshot(path=str(out/'python-packages.png'),animations='disabled');page.locator('#python-requirement').fill('--target ../outside');page.locator('.python-install button').click();expect(page.locator('.python-feedback')).to_contain_text('Invalid package requirement');checks.append('Invalid pip options are rejected and the form displays the real validation error')
                page.locator('[data-python-action=uninstall][data-requirement="zenit-qa-package"]').click();page.wait_for_function('!__qa.p.pythonPackages.data.packages.some(x=>x.name==="zenit-qa-package")',timeout=30000);expect(page.locator('.python-package-list')).not_to_contain_text('zenit-qa-package');checks.append('Project-local removal updates the list while preserving the bundled Python installation')
                page.locator('[data-extension-mode=installed]').click();expect(page.locator('#extension-results')).to_be_visible();assert (ws/'main.py').read_text()=='from zenit_qa_package import VALUE\nprint(VALUE)\n';checks.append('Returning to VSIX extensions retains the project source and the existing extension catalog')
                browser.close()
        finally:app.features.shutdown();app.runner.shutdown();server.shutdown()
    result={'checks':checks,'errors':errors,'packageSource':'Explicit offline verification wheel; real pip and interpreter, no simulated package installation.'};(out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
    if errors:raise AssertionError(errors)

if __name__=='__main__':main()
