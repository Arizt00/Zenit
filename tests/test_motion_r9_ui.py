"""Real dialog lifecycle, interruption, shadow dismissal and screen direction checks."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(label):checks.append(label);print('PASS',label,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-motion-') as tmp:
  base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print(42)\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'en','general.showWelcome':True,'appearance.motion':True,'updates.automatic':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1366,'height':900})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get platform(){return platformUI},get motion(){return motion},modal,closeModal,confirmDialog,openFile};')
    page.route('**/src/app.js',inject);page.on('pageerror',lambda e:errors.append({'name':e.name,'message':e.message,'stack':e.stack}));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
    def finish_open():page.wait_for_function('!document.querySelector("#modal").getAnimations().length')
    def finish_close():page.wait_for_function('!__qa.motion.dialogs.dismissal&&!document.querySelector(".modal-motion-snapshot")')
    page.mouse.move(1150,150);page.wait_for_function('document.querySelector("#lumen-home").style.getPropertyValue("--welcome-x")!==""')
    page.evaluate('__qa.studio.showActivity()');finish_open();frozen=page.locator('.welcome-depth').evaluate('(e)=>getComputedStyle(e).transform')
    page.mouse.move(200,650);assert page.locator('.welcome-depth').evaluate('(e)=>getComputedStyle(e).transform')==frozen
    page.evaluate('__qa.closeModal()');assert page.locator('#modal-backdrop').evaluate('(e)=>e.classList.contains("hidden")');assert page.locator('.profile-activity').count()==0
    assert page.evaluate('!!__qa.motion.dialogs.dismissal&&document.querySelector(".modal-motion-snapshot").inert&&__qa.motion.dialogs.dismissal.element.getAnimations().length>0')
    page.mouse.move(1050,550);assert page.locator('.welcome-depth').evaluate('(e)=>getComputedStyle(e).transform')==frozen
    finish_close();assert not page.evaluate('document.documentElement.dataset.modalMotion');passed('Activity opens and closes progressively while the exact background position stays held through dismissal')

    page.evaluate('__qa.studio.showActivity()');finish_open();page.screenshot(path=str(out/'activity-opened.png'));page.evaluate('()=>{__qa.closeModal();const d=__qa.motion.dialogs.dismissal;for(const a of [d.element,...d.element.children,d.layer].flatMap(e=>e.getAnimations())){a.pause();a.currentTime=115;}window.__closingFrame=__qa.motion.dialogs.frame(d.element);}')
    page.screenshot(path=str(out/'activity-closing.png'));page.evaluate('__qa.studio.showActivity();window.__reopenedFrame=__qa.motion.dialogs.state.element.getAnimations()[0].effect.getKeyframes()[0]')
    frames=page.evaluate('({before:__closingFrame,after:__reopenedFrame})');assert frames['before']['clipPath']==frames['after']['clipPath'] and frames['before']['translate']==frames['after']['translate'],frames
    assert page.locator('.modal-motion-snapshot').count()==0;finish_open();passed('Reopening during dismissal resumes from the visible shape without duplicate live forms or layers')
    page.evaluate('__qa.closeModal()');finish_close();page.evaluate('__qa.studio.showActivity()');page.wait_for_function('__qa.motion.dialogs.state.element.getAnimations().some(a=>a.effect.getTiming().duration===460)')
    page.evaluate('()=>{const e=__qa.motion.dialogs.state.element;for(const a of e.getAnimations()){a.pause();a.currentTime=180;}window.__openingFrame=__qa.motion.dialogs.frame(e);__qa.closeModal();window.__closingStart=__qa.motion.dialogs.dismissal.element.getAnimations()[0].effect.getKeyframes()[0];}')
    frames=page.evaluate('({before:__openingFrame,after:__closingStart})');assert frames['before']['clipPath']==frames['after']['clipPath'] and frames['before']['translate']==frames['after']['translate'],frames
    finish_close();passed('Closing midway through opening starts at the current rendered frame rather than jumping to the full panel')

    page.evaluate('__qa.studio.showActivity()');finish_open();page.locator('#activity-edit-profile').click();expect(page.locator('#profile-form')).to_be_visible();assert page.locator('.modal-motion-snapshot').count()==0;finish_open();passed('Activity to Edit profile transfers the surface without returning to the avatar first')
    data=page.locator('#profile-crop').evaluate('(e)=>e.toDataURL()');page.evaluate('__qa.closeModal()');assert page.evaluate('window.__qa.motion.dialogs.dismissal.element.querySelector("#profile-crop").toDataURL()')==data
    assert page.locator('#profile-form').count()==0 and page.locator('#profile-crop').count()==0;finish_close();passed('Dismissal preserves actual canvas pixels while copied fields and IDs are isolated from application selectors')

    page.evaluate('()=>{__qa.modal("Scroll continuity",`<div id="motion-scroll" style="height:100px;overflow:auto"><div style="height:800px">Scrollable evidence</div></div><input id="motion-check" type="checkbox"><select id="motion-select" multiple><option>a</option><option>b</option></select>`);document.getElementById("motion-scroll").scrollTop=215;document.getElementById("motion-check").checked=true;document.getElementById("motion-select").options[1].selected=true;}');finish_open();page.evaluate('__qa.closeModal()');assert page.evaluate('()=>{const e=__qa.motion.dialogs.dismissal.element;return e.querySelector("#motion-scroll").scrollTop===215&&e.querySelector("#motion-check").checked&&e.querySelector("#motion-select").options[1].selected;}');finish_close();passed('Nested scroll positions and changed checkbox/select values remain visually exact during dismissal')

    page.evaluate('()=>{window.__answer=null;__qa.confirmDialog("Lifecycle check","Continue?","Accept").then(answer=>window.__answer=answer)}');finish_open();page.locator('#confirm-yes').click();page.wait_for_function('__answer===true');assert page.evaluate('!!__qa.motion.dialogs.dismissal');finish_close();passed('Confirmation result resolves immediately and exactly once while its visual close completes separately')
    page.locator('.welcome-profile').focus();page.keyboard.press('Enter');finish_open();page.keyboard.press('Escape');finish_close();assert page.locator('.welcome-profile').evaluate('(e)=>e===document.activeElement');passed('Keyboard dismissal restores the opener after the return animation')

    page.evaluate('__qa.studio.enter()');page.wait_for_function('!__qa.motion.screenTransition');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('window.lumen.activeFile==="main.py"')
    page.evaluate('__qa.platform.settings("appearance")');page.wait_for_function('!__qa.platform.workbench.getAnimations().length');page.evaluate('__qa.platform.closePage()');assert page.evaluate('!!__qa.motion.surfaces.dismissal');page.wait_for_function('!__qa.motion.surfaces.dismissal');passed('Settings has matching surface/background opening and dismissal without blocking the editor')
    assert page.evaluate('()=>{__qa.studio.home();return document.documentElement.dataset.screenMotion==="home";}');page.wait_for_function('!__qa.motion.screenTransition');page.evaluate('__qa.studio.enter();__qa.studio.home();__qa.studio.enter()');page.wait_for_function('!__qa.motion.screenTransition');assert page.evaluate('document.documentElement.dataset.screen==="studio"&&!document.documentElement.dataset.screenMotion');passed('Return home has its own contraction; rapid alternating navigation finishes on the last requested screen')

    page.locator('.avatar').click();finish_open();page.evaluate('__qa.closeModal()');page.set_viewport_size({'width':1100,'height':740});finish_close();assert page.evaluate('document.querySelectorAll(".modal-motion-snapshot").length===0');passed('Resize during dismissal settles and removes visual layers safely')
    page.locator('.avatar').click();finish_open();page.evaluate('__qa.closeModal()');page.emulate_media(reduced_motion='reduce');finish_close();page.evaluate('__qa.studio.editProfile()');assert page.locator('#modal').evaluate('(e)=>e.getAnimations().length===0');page.evaluate('__qa.closeModal();__qa.studio.home()');assert not page.evaluate('__qa.motion.screenTransition||__qa.motion.dialogs.dismissal');passed('Reduced motion also interrupts active dismissal and leaves immediate, functional navigation')
    assert not errors,errors;assert page.locator('.modal-motion-snapshot').count()==0;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
