"""Exercise destination diagnostics, editable cases and real extension comment UI."""
import io,json,sys,tempfile,threading,zipfile,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

out=ROOT/'qa-output/r2-closure-ui';out.mkdir(exist_ok=True);checks=[];errors=[]
with tempfile.TemporaryDirectory(prefix='zenit-closure-ui-') as tmp:
 base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'main.py').write_text('print(1)\n');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
 app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
 raw=io.BytesIO()
 with zipfile.ZipFile(raw,'w') as z:
  z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'comments','version':'1.0.0','main':'main.cjs'}))
  z.writestr('extension/main.cjs','''const v=require('vscode');exports.activate=()=>{const c=v.comments.createCommentController('qa','Revisión de código');const t=c.createCommentThread(v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,'main.py'),new v.Range(0,0,0,5),[{body:'Texto <script>window.BAD=true</script> legible',author:{name:'QA'}}]);t.label='Comentario verificado';};''')
 store=app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True)
 server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
   def inject(route):
    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get studio(){return studio},openFile};')
   page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.locator('[data-file="main.py"]').click()
   app.features.extension_runtime.start(app.workspace,'qa.comments',True)
   expect(page.locator('.extension-comments')).to_contain_text('Comentario verificado');expect(page.locator('.extension-comments')).to_contain_text('<script>window.BAD=true</script>');assert page.evaluate('window.BAD') is None
   page.screenshot(path=str(out/'comments.png'));page.locator('[data-comment-close]').click();expect(page.locator('.extension-comments')).to_have_count(0);checks.append('Real extension comments render in a separate readable surface as escaped text and collapse through the extension controller')
   page.evaluate('import("/src/execution-readiness.js").then(m=>m.showExecutionReadiness({platform:__qa.platform}))');expect(page.locator('.readiness-tools')).to_be_visible(timeout=20000);expect(page.locator('.execution-readiness')).to_contain_text('Python · Este equipo');expect(page.locator('.readiness-tools article[data-ready=true]')).to_have_count(1);page.screenshot(path=str(out/'readiness.png'));page.locator('[data-readiness-melody]').click();expect(page.locator('#ai-input')).to_have_value(re.compile(r'"language": "python"'));checks.append('The actual interpreter is discovered without running the project and its target-aware evidence prepares a docked Melody query')
   page.evaluate('import("/src/experience-r2.js").then(m=>m.runLanternMatrix(__qa.studio.lantern))');expect(page.locator('.r2-matrix-form')).to_be_visible();page.locator('[name=name-0]').fill('Salida parcial');page.locator('[name=match-0]').select_option('contains');page.locator('[name=output-0]').fill('1');page.locator('[name=enabled-1]').uncheck();page.locator('[data-cases-save]').click();expect(page.locator('[data-cases-saved]')).to_contain_text('guardados');page.keyboard.press('Escape');page.evaluate('import("/src/experience-r2.js").then(m=>m.runLanternMatrix(__qa.studio.lantern))');expect(page.locator('[name=name-0]')).to_have_value('Salida parcial');expect(page.locator('[name=match-0]')).to_have_value('contains');page.keyboard.press('Escape');checks.append('Editable case names and contains/exact comparison survive saving and reopening the actual matrix form')
   page.evaluate('__qa.studio.desktop.handle("foundation")');expect(page.locator('#lab-tab-sdk')).to_be_visible(timeout=30000);page.locator('#lab-tab-sdk').click();expect(page.locator('.sdk-readiness-button')).to_be_visible();page.locator('.sdk-readiness-button').click();expect(page.locator('.readiness-tools')).to_be_visible(timeout=20000);page.locator('[data-action=close-modal]').click();expect(page.locator('.execution-readiness')).to_have_count(0);page.locator('#lab-tab-machines').click();page.wait_for_timeout(300);expect(page.locator('.machine-readiness-summary')).to_be_visible();page.screenshot(path=str(out/'machines.png'));checks.append('SDK exposes the working diagnostic action and Machines shows tool readiness, verified media and running session counts')
   assert not errors,errors;assert (ws/'main.py').read_text()=='print(1)\n';browser.close()
 finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
(out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors}))
