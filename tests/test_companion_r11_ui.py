"""Actual Lantern runs and prompt/context behavior; AI and model catalogs are declared fixtures."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(label):checks.append(label);print('PASS',label,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-companion-') as tmp:
  base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('print("VALUE ONE")\n');(ws/'other.py').write_text('print("OTHER FILE")\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.locale':'en','general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'security.confirmRoutineActions':False,'ai.provider':'ollama','ai.model':'declared-companion-fixture'})
  requests=[]
  def transport(job,messages,system,key):requests.append(messages);job.append('Declared consultation fixture: inspect the observed exit and output before changing code.');job.done=True
  app.features.ai._run=transport;app.features.ai.models=lambda provider,consent:{'models':['declared-companion-fixture'],'verified':False,'note':'Declared catalog fixture, not a live account.'}
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1672,'height':917})
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get editor(){return editor},get p(){return platformUI},openFile};')
    page.route('**/src/app.js',inject);page.on('pageerror',lambda e:errors.append(e.message));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")')
    page.locator('.melody-utilities-toggle').click();page.locator('[data-utility-tab=context]').click();expect(page.locator('.melody-workflow pre')).to_contain_text('VALUE ONE');page.locator('#ai-input').fill('Explain the observable behavior');page.locator('[data-draft-save]').click();expect(page.locator('[data-draft-load]')).to_have_count(1)
    page.evaluate('__qa.p.setMelodyMode("edit")');page.locator('#ai-input').fill('Temporary text');page.locator('[data-draft-load]').click();assert page.locator('#ai-input').input_value()=='Explain the observable behavior';assert page.evaluate('__qa.p.melodyMode==="chat"');assert not requests;passed('Melody previews actual scoped code and restores prompt drafts in Chat without sending')
    page.evaluate('__qa.p.savePreference("ai.context","none")');expect(page.locator('.melody-workflow pre')).to_contain_text('No code is attached');page.evaluate('__qa.p.savePreference("ai.context","file")');page.screenshot(path=str(out/'melody-context.png'),animations='disabled');page.locator('[data-utilities-close]').click();passed('Context preview follows the actual No code/Whole file preference')

    page.evaluate('__qa.studio.lantern.action("start")');page.wait_for_function('__qa.studio.lantern.state.status==="watching"&&__qa.studio.lantern.state.output.includes("VALUE ONE")',timeout=30000)
    expect(page.locator('#lantern-inline form input')).to_have_attribute('placeholder','Program input · Enter');expect(page.locator('#lantern-inline form button').first).to_have_attribute('aria-label','Send input')
    revision=page.evaluate('__qa.studio.lantern.state.revision');page.evaluate('__qa.editor.view.getModel().setValue(\'print("VALUE TWO")\\n\')');page.wait_for_function('(r)=>__qa.studio.lantern.state.revision>r&&__qa.studio.lantern.state.status==="watching"&&__qa.studio.lantern.state.output.includes("VALUE TWO")',arg=revision,timeout=30000)
    page.locator('#lantern-inline .lantern-review summary').click();expect(page.locator('#lantern-inline .output-added').filter(has_text='VALUE TWO')).to_have_count(1);expect(page.locator('#lantern-inline .output-removed').filter(has_text='VALUE ONE')).to_have_count(1);assert (ws/'main.py').read_text()=='print("VALUE ONE")\n';page.locator('#lantern-inline .output-added').filter(has_text='VALUE TWO').scroll_into_view_if_needed();page.screenshot(path=str(out/'lantern-revisions.png'),animations='disabled');passed('Two actual Python buffer executions produce a bounded output comparison while disk remains unchanged')
    page.locator('#lantern-inline [data-lantern=pin]').click();page.wait_for_function('__qa.p.prefs["lantern.followActive"]===false');current=page.evaluate('__qa.studio.lantern.state.revision');page.evaluate('__qa.openFile("other.py")');page.wait_for_timeout(900);assert page.evaluate('__qa.studio.lantern.state.path==="main.py"&&__qa.studio.lantern.state.revision=== '+str(current));page.evaluate('__qa.editor.view.getModel().setValue(\'print("OTHER UNSAVED")\\n\')');page.wait_for_timeout(900);assert page.evaluate('__qa.studio.lantern.state.path==="main.py"&&__qa.studio.lantern.state.revision=== '+str(current));passed('Pinning preserves the executed file and ignores unrelated active-tab edits')
    page.locator('#lantern-inline [data-lantern=pin]').click();page.wait_for_function('__qa.studio.lantern.state.path==="other.py"&&__qa.studio.lantern.state.output.includes("OTHER UNSAVED")',timeout=30000);passed('Restoring Follow active file actually starts the other unsaved buffer')
    page.evaluate('__qa.p.setMelodyMode("edit")');page.locator('#lantern-inline [data-lantern=analyze]').click();page.wait_for_function('!__qa.p.aiJob&&!__qa.p.aiStarting');expect(page.locator('.floating-panel[data-floating-panel=assistant]')).to_be_visible();expect(page.locator('#chat-messages')).to_contain_text('Declared consultation fixture');assert requests and 'Review this observed Lantern execution' in json.dumps(requests[-1]);assert page.evaluate('__qa.p.melodyMode==="chat"');assert (ws/'main.py').read_text()=='print("VALUE ONE")\n' and (ws/'other.py').read_text()=='print("OTHER FILE")\n';passed('Analyze Lantern opens floating Melody and actually sends a bounded read-only consultation')
    page.evaluate('__qa.p.savePreference("ai.model","")');page.locator('#lantern-inline [data-lantern=analyze]').click();expect(page.locator('#melody-model-picker')).to_be_visible();assert page.evaluate('__qa.p.page!=="settings"');expect(page.locator('[data-model-id]')).to_have_count(1);page.keyboard.press('Escape');passed('Missing model opens the inline picker and preserves the Lantern prompt instead of navigating to Settings')
    page.evaluate('__qa.studio.lantern.action("stop")');assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'aiTransport':'Declared deterministic fixture; actual Python processes execute the unsaved buffers.'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
