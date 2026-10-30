"""Actual browser UI, a real Python journey, and readable performance phases."""
import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

out=ROOT/'qa-output/startup-depth-ui';out.mkdir(exist_ok=True);errors=[];checks=[]
with tempfile.TemporaryDirectory(prefix='zenit-startup-depth-ui-',ignore_cleanup_errors=True) as temp:
 root=Path(temp);project=root/'project';project.mkdir();(project/'main.py').write_text('value=42\nprint(value)\n')
 app=Application(ROOT,project,data_dir=root/'profile');f=app.features;app.workspace.trusted=True
 f.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False});f.studio.update({'onboarded':True})
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get desktop(){return desktopUI},get platform(){return platformUI},openFile};')
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('__qa.openFile("main.py")')
   page.evaluate('__qa.desktop.handle("performance-report")');expect(page.locator('.performance-measured')).to_contain_text('Fases medidas del servicio');expect(page.locator('.performance-measured')).to_contain_text('core-services');expect(page.locator('.performance-measured')).to_contain_text('Servicios bajo demanda')
   page.wait_for_function('()=>!document.querySelector("#modal").getAnimations({subtree:true}).some(a=>a.playState==="running"&&a.effect?.getComputedTiming().iterations!==Infinity)');page.screenshot(path=str(out/'performance-day.png'));assert 'machines' not in f.__dict__;assert 'python_packages' not in f.__dict__;checks.append('Opening the performance report measures phases without starting QEMU or package managers')
   page.evaluate('__qa.desktop.handle("language-verification")');expect(page.locator('.language-journeys article')).to_have_count(7);page.locator('.nc-reference summary').click();expect(page.locator('.nc-reference')).to_contain_text('1.0.0.21v');expect(page.locator('.nc-reference')).to_contain_text('El PSI de IntelliJ no se ejecuta');checks.append('nC reference names exact selected distribution and distinguishes native/adapted/missing without asserting parity')
   page.locator('[data-journey="python"]').click();expect(page.locator('[data-journey-state]')).to_contain_text('Comprobando',timeout=10000)
   page.wait_for_function('()=>[...document.querySelectorAll(".language-journeys article")].some(a=>a.querySelector("h4")?.textContent==="Python"&&a.textContent.includes("6 de 6 pasos comprobados"))',timeout=90000)
   assert (project/'main.py').read_text()=='value=42\nprint(value)\n';checks.append('An explicit Python journey runs real LSP definition/rename, compile/run, unittest and debugger stepping on a disposable sample')
   page.screenshot(path=str(out/'language-journeys-day.png'))
   page.evaluate('__qa.platform.savePreference("appearance.theme","dark")');page.wait_for_timeout(500);page.screenshot(path=str(out/'language-journeys-dark.png'))
   page.evaluate('__qa.platform.host.closeModal()');page.evaluate('__qa.desktop.handle("forge-terminal")');page.wait_for_function('__qa.desktop.forgeTools!==null&&__qa.desktop.forgeTools!==undefined');checks.append('Opening Forge explicitly loads its deferred tool inventory');assert not errors,errors;browser.close()
 finally:server.shutdown();server.server_close();f.shutdown();app.runner.shutdown()
(out/'report.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'checks':checks,'errors':errors},ensure_ascii=True))
