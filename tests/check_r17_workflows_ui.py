import json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

out=ROOT/'qa-output/r17-workflows-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
with tempfile.TemporaryDirectory(prefix='zenit-r17-workflows-') as folder:
 base=Path(folder);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('print(42)\n');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
 app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
 gate=threading.Event();started=threading.Event();first=app.features.hilo.submit('Preparar entorno',lambda e:(started.set(),gate.wait(30)),workspace=ws);assert started.wait(3)
 second=app.features.hilo.submit('Compilar después',lambda e:None,workspace=ws,depends=[first['job']]);server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get studio(){return studio}};')
   context.route('**/src/app.js',inject);page=context.new_page();page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady')
   page.locator('.task-center-toggle').click();expect(page.locator('.task-center-card')).to_have_count(2);expect(page.locator('.task-center-card').filter(has_text='Compilar después')).to_contain_text('Preparar entorno');page.screenshot(path=str(out/'tasks.png'))
   select=page.locator('[data-task-id="'+second['job']+'"] select');select.select_option('-20');page.wait_for_function('(id)=>document.querySelector(`[data-task-id="${id}"] select`).value==="-20"',arg=second['job']);assert next(j for j in app.features.hilo.snapshot(ws)['jobs'] if j['id']==second['job'])['priority']==-20
   page.locator('[data-task-id="'+first['job']+'"] [data-task-cancel]').click();gate.set();expect(page.locator('[data-task-id="'+second['job']+'"]')).to_contain_text('Cancelada',timeout=12000);checks.append('Task center displays prerequisites, changes actual queue priority and cancels dependents')
   page.evaluate('__qa.platform.closePage()');page.locator('.foundation-toggle').click();page.locator('[data-lab-section="sessions"]').click();expect(page.locator('.tern-portability')).to_be_visible();page.screenshot(path=str(out/'lantern-empty.png'));checks.append('Lantern export and reconstruction controls mount without losing session forms')
   page.locator('.session-create [name=name]').fill('Portable UI');page.locator('.session-create [name=inherit]').select_option('false');page.locator('.session-create button[type=submit]').click();expect(page.locator('.session-card')).to_have_count(1,timeout=90000);expect(page.locator('.session-feedback')).to_have_text('Listo.');page.locator('.session-save input').fill('portable-ui.tern');page.locator('.session-save button').click();expect(page.locator('[data-tern-export] select')).to_have_value('portable-ui.tern',timeout=12000)
   page.locator('[data-tern-export] > button').click();expect(page.locator('.tern-portability-report')).to_contain_text('falta su rueda',timeout=20000);page.screenshot(path=str(out/'lantern-resource-report.png'));assert (ws/'portable-ui.tern.zip').is_file();checks.append('Real UI creates a reproducible descriptor and exports a bundle with its missing-wheel report')
   page.locator('[data-tern-inspect]').click();expect(page.locator('[data-tern-rebuild]')).to_be_disabled();checks.append('An incomplete bundle cannot enable reconstruction')
   page.evaluate('__qa.platform.closePage();__qa.platform.settings("connections")');expect(page.locator('.extension-account input[type=password]')).to_be_visible(timeout=15000);page.screenshot(path=str(out/'extension-accounts.png'));assert not errors,errors;checks.append('Connection settings show an empty GitHub account form and do not invent an identity')
   for width,height in [(1280,720),(1920,1080)]:
    page.set_viewport_size({'width':width,'height':height});page.screenshot(path=str(out/f'accounts-{width}.png'));assert page.locator('.extension-account').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
   browser.close()
 finally:gate.set();server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');print('PASS',checks)
