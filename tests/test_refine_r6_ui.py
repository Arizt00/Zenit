"""R6 regressions: actual Monaco, real Python/ConPTY; declared AI fixtures."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(s):checks.append(s);print('PASS',s,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-refine-') as tmp:
  base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print("Hello from the R6 execution workspace")\n',encoding='utf-8')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'})
  app.features.prefs.update({'general.showWelcome':False,'general.locale':'en','updates.automatic':False,'security.confirmRoutineActions':False,'terminal.confirmClose':False,'appearance.motion':False})
  requests=[]
  def transport(job,messages,system,key):requests.append(messages);job.append('Declared test response: inspect the paused frame before continuing.');job.done=True
  app.features.ai._run=transport
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get dock(){return dock},get editor(){return editor},get platform(){return platformUI},get desktop(){return desktopUI},get foundation(){return foundationUI},openFile};')
    context.route('**/src/app.js',inject);page=context.new_page();page.on('pageerror',lambda e:errors.append(e.stack));page.goto(url);page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.studio.enter()');page.evaluate('__qa.openFile("main.py")')
    for theme in ('day','dark','forest'):
     page.evaluate('(t)=>__qa.platform.savePreference("appearance.theme",t)',theme);expect(page.locator('html')).to_have_attribute('data-theme',theme)
     tab=page.locator('.file-tab.active');assert tab.evaluate('(e)=>parseFloat(getComputedStyle(e).borderTopLeftRadius)')>=10
     assert tab.evaluate('(e)=>getComputedStyle(e).backgroundColor')==page.locator('#editor-mount').evaluate('(e)=>getComputedStyle(e).backgroundColor')
     assert tab.evaluate('(e)=>getComputedStyle(e).boxShadow')=='none'
     assert page.evaluate('()=>{const s=getComputedStyle(document.documentElement),rgb=v=>[1,3,5].map(i=>parseInt(v.slice(i,i+2),16)/255),lum=v=>rgb(v).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((a,c,i)=>a+c*[.2126,.7152,.0722][i],0),bg=lum(s.getPropertyValue("--surface").trim());return ["--text","--secondary","--muted"].every(k=>{const fg=lum(s.getPropertyValue(k).trim());return (Math.max(bg,fg)+.05)/(Math.min(bg,fg)+.05)>=4.5;});}')
     page.screenshot(path=str(out/f'workspace-{theme}.png'),animations='disabled')
    passed('Three built-in themes: rounded active tab joins code background without an accent underline')
    assert page.evaluate('async()=>{const p=__qa.platform,api=p.api,write=p.settingsWrite,model=p.prefs["ai.model"];let release,calls=0;p.settingsWrite=new Promise(r=>release=r);p.api=async()=>{calls++;return {settings:{...p.prefs,"ai.model":"stale-model"}};};const pending=p.syncPreferences();p.preferenceEpoch=(p.preferenceEpoch||0)+1;p.settingsWrite=Promise.resolve();p.prefs["ai.model"]="new-model";release();await pending;const ok=calls===0&&p.prefs["ai.model"]==="new-model";p.api=api;p.settingsWrite=write;p.prefs["ai.model"]=model;return ok;}');passed('A preference read overtaken by a newer write cannot restore a stale model')
    await_state=page.evaluate('__qa.dock.snapshot()');page.evaluate('()=>__qa.platform.extensions()');expect(page.locator('#platform-page')).to_be_visible();expect(page.locator('#project-panel')).not_to_be_visible();expect(page.locator('#assistant-panel')).not_to_be_visible()
    assert page.locator('#project-panel').evaluate('(e)=>e.inert');assert page.evaluate('__qa.dock.snapshot()')==await_state
    page.screenshot(path=str(out/'extensions.png'),animations='disabled');page.evaluate('__qa.platform.closePage()');assert page.evaluate('__qa.dock.snapshot()')==await_state;expect(page.locator('#project-panel')).to_be_visible();expect(page.locator('#assistant-panel')).to_be_visible();passed('Extensions isolates content and restores the unchanged dock state')
    page.evaluate('()=>__qa.platform.settings("ai")');expect(page.locator('.provider-card .provider-kind')).to_have_count(9)
    assert page.locator('.provider-card .provider-brand').count()==8;assert page.locator('.provider-card .provider-kind').count()==9
    page.screenshot(path=str(out/'providers.png'),animations='disabled');page.evaluate('__qa.platform.closePage()');passed('All nine destinations have a recognizable identity and Account/API/Local type')
    page.evaluate('async()=>{await __qa.platform.savePreference("ai.provider","ollama");await __qa.platform.savePreference("ai.model","explicit-r6-fixture");await __qa.studio.debug();}')
    page.evaluate('()=>{__qa.studio.debugWorkspace.state={path:"main.py",status:"paused",line:1,variables:[{name:"count",value:"3",type:"int"}],stack:[{name:"main",path:"main.py",line:1}],output:"Debugger ready"};__qa.platform.melodyMode="edit";}')
    page.locator('[data-debug-analyze]').click();expect(page.locator('.floating-panel[data-floating-panel=assistant]')).to_be_visible();expect(page.locator('.chat-message.assistant')).to_contain_text('Declared test response',timeout=15000)
    payload=json.dumps(requests[-1]);assert 'Debugger ready' in payload and 'count' in payload and 'EDICIÓN EN VIVO AUTORIZADA' not in payload;assert page.evaluate('__qa.editor.getValue()')=='print("Hello from the R6 execution workspace")\n'
    page.screenshot(path=str(out/'debug-melody.png'),animations='disabled');passed('Debug opens floating Melody and submits a read-only session snapshot even from Edit mode')
    page.evaluate('__qa.platform.closePage()');page.locator('.melody-utilities-toggle').click();page.locator('[data-melody-task=tests]').click();expect(page.locator('.chat-message.assistant')).to_have_count(2,timeout=15000);assert 'test plan' in json.dumps(requests[-1]);passed('Plan tests sends the scoped source to a read-only request')
    page.evaluate('()=>__qa.platform.diagnosticMap.set("main.py",[{message:"Fixture syntax diagnostic",line:1,severity:"error"}])');page.locator('.melody-utilities-toggle').click();page.locator('[data-melody-task=diagnostics]').click();expect(page.locator('.chat-message.assistant')).to_have_count(3,timeout=15000);assert 'Fixture syntax diagnostic' in json.dumps(requests[-1]);passed('Review diagnostics includes actual editor diagnostic records')
    page.evaluate('()=>__qa.desktop.openForgeTerminal()');page.locator('.forge-file-run').click();page.wait_for_function('()=>__qa.desktop.forgeRun?.terminal&&__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal)?.closed',timeout=30000);expect(page.locator('.forge-session-detail')).to_contain_text('exit 0');page.locator('[data-action=forge-analyze]').click();expect(page.locator('.chat-message.assistant')).to_have_count(4,timeout=15000);assert 'Hello from the R6 execution workspace' in json.dumps(requests[-1]);page.screenshot(path=str(out/'forge-melody.png'),animations='disabled');passed('Forge runs real Python and sends its captured output and exit code to Melody')
    page.locator('.foundation-toggle').click();expect(page.locator('.lab-project-context')).to_be_visible();expect(page.locator('#project-panel')).not_to_be_visible();expect(page.locator('#assistant-panel')).not_to_be_visible();expect(page.locator('#terminal-panel')).to_be_visible();page.screenshot(path=str(out/'laboratory.png'),animations='disabled');page.locator('[data-lab-assist]').click();expect(page.locator('.chat-message.assistant')).to_have_count(5,timeout=15000);assert 'available' in json.dumps(requests[-1]);passed('Laboratory connects detected tool readiness with Forge and a real setup-context request')
    page.evaluate('()=>__qa.dock.move("assistant","left")');saved=page.evaluate('__qa.dock.snapshot()');page.evaluate('()=>__qa.platform.extensions()');page.evaluate('__qa.platform.closePage()');assert page.evaluate('__qa.dock.snapshot()')==saved;passed('Grouped panels survive contextual view switching without state loss')
    page.set_viewport_size({'width':1366,'height':768});page.evaluate('__qa.dock.reset()');page.screenshot(path=str(out/'workspace-1366.png'),animations='disabled');assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');passed('Compact workspace has no horizontal page overflow')
    page.emulate_media(reduced_motion='reduce');assert page.evaluate('window.lumen.motionEnabled') is False;assert not errors,errors;passed('Reduced motion and browser error checks pass');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'aiTransport':'Explicit fixture; verifies context/actions only.','terminal':'Actual Windows ConPTY/Python'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
