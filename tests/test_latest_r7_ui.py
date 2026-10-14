"""Latest steering: inline models, original factory extension and screen motion."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.factory_extensions import install_factory
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(label):checks.append(label);print('PASS',label,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-latest-') as tmp:
  base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print(42)\n');(ws/'hello.nc').write_text('stc main() { return 0; }\n');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
  install_factory(app.features.extensions,ROOT);app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'en','general.showWelcome':False,'updates.automatic':False,'appearance.motion':True})
  calls=[]
  def catalog(provider,consent):calls.append(provider);return {'models':['declared-model-a','declared-model-b'],'verified':False,'note':'Explicit catalog fixture for UI behavior; not a live account.'}
  app.features.ai.models=catalog
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get editor(){return editor},get platform(){return platformUI},get motion(){return motion},openFile};')
    context.route('**/src/app.js',inject);page=context.new_page();page.on('pageerror',lambda e:errors.append(e.stack));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")')
    assert page.evaluate('__qa.platform.extensionContributions.grammars.some(g=>g.owner==="nc-lang.nc-language")');assert page.evaluate('!document.documentElement.dataset.iconArrows||document.documentElement.dataset.iconArrows==="visible"');passed('Original factory nC grammar loads; its icon theme is not automatically selected')
    before=page.locator('.file-tab.active .file-type').evaluate('(e)=>e.outerHTML');page.evaluate('__qa.openFile("hello.nc")');expect(page.locator('.file-tab.active .file-type-nc img')).to_have_count(1);page.evaluate('__qa.openFile("main.py")');assert page.locator('.file-tab.active .file-type').evaluate('(e)=>e.outerHTML')==before;passed('nC icon changes leave Python identity unchanged')
    page.locator('.assistant-heading-title h2').click();expect(page.locator('#melody-model-picker')).to_be_visible();expect(page.locator('[data-model-id]')).to_have_count(2);assert page.evaluate('!__qa.platform.page');page.screenshot(path=str(out/'melody-model-picker.png'),animations='disabled');page.locator('[data-model-id="declared-model-b"]').click();expect(page.locator('#melody-model-picker')).not_to_be_visible();page.wait_for_function('__qa.platform.prefs["ai.model"]==="declared-model-b"');passed('Clicking Melody fetches and selects models in a subpanel without opening Settings')
    n=len(calls);page.locator('.melody-destination').click();expect(page.locator('[data-model-id]')).to_have_count(2);assert len(calls)==n;page.locator('[data-model-search]').fill('model-a');expect(page.locator('[data-model-id]:visible')).to_have_count(1);page.keyboard.press('Escape');expect(page.locator('#melody-model-picker')).not_to_be_visible();passed('Destination uses cached catalogs, filter and Escape; no false account-verification state')
    page.evaluate('__qa.studio.home()');page.mouse.move(1400,100);page.wait_for_function('document.querySelector("#lumen-home").style.getPropertyValue("--welcome-x")!==""');before=page.evaluate('({x:document.querySelector("#lumen-home").style.getPropertyValue("--welcome-x"),y:document.querySelector("#lumen-home").style.getPropertyValue("--welcome-y")})');page.evaluate('__qa.studio.showActivity()');page.wait_for_function('document.querySelector("#modal").getAnimations().length===0');page.mouse.move(800,450);after=page.evaluate('({x:document.querySelector("#lumen-home").style.getPropertyValue("--welcome-x"),y:document.querySelector("#lumen-home").style.getPropertyValue("--welcome-y")})');assert before==after,(before,after);page.keyboard.press('Escape');passed('Opening Activity and leaving the home surface preserves its parallax position')
    page.evaluate('()=>{window.__transitionSeen=false;const swap=__qa.motion.swapScreen.bind(__qa.motion);__qa.motion.swapScreen=(...args)=>{__transitionSeen=true;return swap(...args)};}');page.evaluate('__qa.studio.enter()');assert page.evaluate('__transitionSeen&&document.documentElement.dataset.screen==="studio"');page.locator('.brand').click();page.wait_for_function('document.documentElement.dataset.screen==="home"&&!__qa.motion.screenTransition');passed('Entering the IDE and clicking Zénit back home use the continuous view transition')
    page.evaluate('__qa.studio.enter()');page.locator('.avatar').click();expect(page.locator('#profile-form')).to_be_visible();assert page.evaluate('document.querySelector("#modal").getAnimations().some(a=>a.effect.getKeyframes().some(k=>k.clipPath))');page.locator('#modal').evaluate('(e)=>Promise.all(e.getAnimations().map(a=>a.finished.catch(()=>{})))');page.screenshot(path=str(out/'profile-morph.png'),animations='disabled');page.keyboard.press('Escape');passed('IDE profile opens with the same source-connected morph')
    page.emulate_media(reduced_motion='reduce');page.evaluate('__qa.studio.home()');assert not page.evaluate('__qa.motion.screenTransition');assert not errors,errors;passed('Reduced motion switches screens immediately and all flows have no uncaught errors');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'catalog':'Explicit deterministic fixture; no account verification claim.'},indent=2)+'\n')
if __name__=='__main__':main()
