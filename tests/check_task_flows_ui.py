"""Task-oriented screens against a disposable backend and real local operations."""
import hashlib,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.server import Application,LumenServer
from backend import foundation
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/task-flows';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];previous=foundation._additional_roots
 with tempfile.TemporaryDirectory(prefix='zenit-task-flows-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();source='print("task result 42")\n';(ws/'main.py').write_text(source);(ws/'fail.py').write_text('raise ValueError("expected QA failure")\n')
  sdk=base/'sdk';sdk.mkdir();(sdk/'base.qcow2').write_bytes(b'QFI\xfb'+bytes(4096));digest=hashlib.sha256((sdk/'base.qcow2').read_bytes()).hexdigest();(sdk/'tool-index.json').write_text(json.dumps({'schema':1,'platform':sys.platform,'tools':{},'components':[{'id':'arch','name':'QA resource base','file':'base.qcow2','sha256':digest}]}))
  medium=base/'checksum-fixture.iso';medium.write_bytes(b'Checksum verification fixture, not a bootable guest.'*300);media_hash=hashlib.sha256(medium.read_bytes()).hexdigest()
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get p(){return platformUI},get desktop(){return desktopUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.p.host.editor.current==="main.py"')
    def result(scope,state):expect(page.locator(scope+' .task-flow-card:visible')).to_have_attribute('data-state',state,timeout=60000)
    def step(scope,n):assert page.locator(scope+' [aria-current=step]:visible').get_attribute('data-flow-step')==str(n)
    def review(scope):page.locator(scope+' [data-flow-run]:visible').wait_for();step(scope,2)
    def execute(scope):page.locator(scope+' [data-flow-run]:visible').evaluate('(b)=>{b.click();b.click();}')
    def visual(scope,name):
     for theme,width in [('day',1600),('dark',1280),('forest',1024)]:
      page.evaluate('(theme)=>__qa.p.savePreference("appearance.theme",theme)',theme);page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(220)
      assert page.locator(scope+' .task-flow-steps:visible').count()==1
      assert page.locator(scope).evaluate('(n)=>n.scrollWidth<=n.clientWidth+1'),(name,theme)
      assert page.locator(scope+' .task-flow-steps:visible').evaluate('(n)=>n.scrollWidth<=n.clientWidth+1'),(name,theme,'steps')
      page.screenshot(path=str(out/(name+'-'+theme+'.png')))
     page.set_viewport_size({'width':1600,'height':1000});page.evaluate('__qa.p.savePreference("appearance.theme","day")')
    page.evaluate('__qa.desktop.handle("project-workflows")');scope='.project-workflows';assert page.locator('.project-runner').is_visible();assert not page.locator('.project-kit-section').is_visible();count=len(app.runner.jobs)
    page.locator('[data-workflow-action=run]').click();review(scope);assert len(app.runner.jobs)==count
    page.locator('#workflow-path').fill('fail.py');assert not page.locator('#workflow-run-plan').is_visible();step(scope,1)
    page.locator('[data-workflow-action=run]').click();review(scope);execute(scope);result(scope,'error');assert len(app.runner.jobs)==count+1;expect(page.locator('#workflow-history')).to_contain_text('expected QA failure');checks.append('Project review is invalidated by edits; a failed real process remains an error with its output')
    page.locator('#workflow-path').fill('main.py');page.locator('[data-workflow-action=run]').click();review(scope);execute(scope);result(scope,'success');step(scope,4);assert len(app.runner.jobs)==count+2;expect(page.locator('#workflow-history')).to_contain_text('task result 42');page.get_by_role('button',name='Ver salida',exact=True).click();assert page.locator('#workflow-history details[open]').count()==1;checks.append('Double execution starts only one real process; its receipt remains on the Project screen')
    page.locator('[data-task-choice=new]').click();assert not page.locator('.project-runner').is_visible();page.locator('[data-kit=python]').click();page.locator('#workflow-kit-folder').fill('new-python');page.locator('[data-kit-plan=python]').click();review(scope);assert not (ws/'new-python').exists();execute(scope);result(scope,'success');assert (ws/'new-python/src/zenit_app/main.py').is_file();checks.append('Project creation uses the same inline review and shows a result without replacing the current editor file');visual(scope,'project');page.get_by_role('button',name='Abrir archivo de inicio',exact=True).click();page.wait_for_function('__qa.p.host.editor.current==="new-python/src/zenit_app/main.py"')
    page.evaluate('__qa.desktop.handle("foundation")');page.locator('#lab-tab-sdk').click();scope='.sdk-manager';page.locator('[data-sdk-root] input').fill(str(sdk));page.locator('[data-sdk-root] button').click();review(scope);assert str(sdk) not in app.features.sdk.config['roots'];execute(scope);result(scope,'success');assert str(sdk) in app.features.sdk.config['roots'];checks.append('SDK activation is deferred until review and records a verified real base in the active inventory');visual(scope,'sdk')
    page.locator('[data-sdk-root] input').fill(str(base/'missing'));page.locator('[data-sdk-root] button').click();execute(scope);result(scope,'error');assert str(base/'missing') not in app.features.sdk.config['roots'];checks.append('Invalid SDK paths show the backend error and never report success')
    page.locator('#lab-tab-machines').click();scope='.machine-library';page.locator('[data-media-import] [name=path]').fill(str(medium));page.locator('[data-media-import] [name=name]').fill('QA checksum medium');page.locator('[data-media-import] [name=sha256]').fill('0'*64);page.locator('[data-media-import] button[type=submit]').click();review(scope);assert not app.features.machine_images.images;execute(scope);result(scope,'error');assert not app.features.machine_images.images;expect(page.locator(scope+' .task-flow-feedback')).to_contain_text('SHA-256');checks.append('Machine import rejects an incorrect checksum and preserves the original medium')
    page.locator('[data-media-import] [name=sha256]').fill(media_hash);page.locator('[data-media-import] button[type=submit]').click();review(scope);execute(scope);result(scope,'success');assert len(app.features.machine_images.images)==1;assert medium.is_file();checks.append('Verified media import finishes in the same review/result surface after the asynchronous backend job');visual(scope,'machines')
    page.locator('#lab-tab-project').click();scope='.foundation-page';page.locator('.lab-ssh-details').wait_for(state='hidden');# standards form is inside details
    page.locator('#lab-standards').evaluate('(n)=>n.closest("details").open=true');page.locator('#lab-standards [name=c]').select_option('c17');page.locator('#lab-standards button.secondary-button').click();review(scope);execute(scope);result(scope,'success');assert app.features.runtimes.config['languages']['c']['standard']=='c17';checks.append('Laboratory configuration reviews and saves actual language settings');visual(scope,'laboratory')
    page.locator('#lab-tab-machines').click();page.locator('.lab-ssh-details summary').click();page.locator('#lab-ssh [name=host]').fill('192.0.2.25');page.locator('#lab-ssh [name=user]').fill('qa');count=len(app.features.machines.snapshot()['profiles']);page.locator('#lab-ssh button.secondary-button').click();review('.machine-library');assert len(app.features.machines.snapshot()['profiles'])==count;page.locator('#lab-ssh [name=host]').fill('192.0.2.26');assert not page.locator('.machine-library [data-flow-run]').is_visible();page.locator('#lab-ssh button.secondary-button').click();review('.machine-library');execute('.machine-library');result('.machine-library','success');assert len(app.features.machines.snapshot()['profiles'])==count+1;checks.append('SSH profile review creates one connection descriptor without connecting or starting a process')
    page.evaluate('__qa.p.extensions("native")');page.locator('.native-packages').wait_for();scope='.native-packages';page.locator('[data-native-language=cpp]').click();page.locator('#native-requirement').fill('--target ../outside');page.locator('.python-install button').click();review(scope);count=len(app.runner.jobs);execute(scope);result(scope,'error');assert len(app.runner.jobs)==count;checks.append('Native dependency review shows its language and manager; invalid input stays an error without starting a process');visual(scope,'native')
    assert (ws/'main.py').read_text()==source;assert not errors,errors;checks.append('Three themes and three window sizes retain aligned task steps; source is unchanged and no browser exceptions occurred');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown();foundation.set_sdk_roots(previous)
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'limits':'Media fixture checks checksum/copy only; it is not a bootable guest or a remote workstation.'},ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
