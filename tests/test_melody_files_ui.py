"""Real file plan/docking/ConPTY UI with an explicitly deterministic AI transport."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(text):checks.append(text);print('PASS',text,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-files-ui-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'old.py').write_text('print("old")\n');(ws/'keep.py').write_text('print("keep")\n')
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'ai.provider':'ollama','ai.model':'qa-fixture','terminal.confirmClose':False})
  proposal={'summary':'Proyecto Python con documentación y prueba','operations':[{'kind':'create','path':'sample/src/main.py','content':'print(42)\n'},{'kind':'create','path':'sample/README.md','content':'# Sample\nRun src/main.py\n'},{'kind':'create','path':'sample/test_main.py','content':'def test_answer():\n    assert 40+2==42\n'},{'kind':'delete','path':'old.py'}]}
  def transport(job,messages,system,hkey):
   assert 'Return ONLY a JSON' in system;job.append(json.dumps(proposal));job.done=True
  app.features.ai._run=transport
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1672,'height':917});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:None)
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get dock(){return dock},get editor(){return editor},get platform(){return platformUI},get desktop(){return desktopUI},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
    # Test plain keyboard input, not the service write endpoint.
    ids=[]
    for index in range(3):
     ids.append(page.evaluate('async()=> (await __qa.platform.openTerminal("cmd")).id'))
     page.wait_for_function('(id)=>__qa.platform.terminals.get(id).xterm.buffer.active.length>0',arg=ids[-1]);page.locator(f'.pty-session[data-session-id="{ids[-1]}"] .xterm-screen').click();page.keyboard.type(f'echo ZENIT_PTY_{index}');page.keyboard.press('Enter')
     page.wait_for_function('([id,marker])=>{const b=__qa.platform.terminals.get(id).xterm.buffer.active;return Array.from({length:b.length},(_,i)=>b.getLine(i)?.translateToString(true)).some(x=>x===marker);}',arg=[ids[-1],f'ZENIT_PTY_{index}'],timeout=15000)
    passed('Three separate real CMD/ConPTY terminals accept keyboard input')
    for index in (0,2,1,0):
     page.locator('.zenit-terminal-picker').click();page.locator('.menu-item').filter(has_text='Símbolo del sistema').nth(index).click();page.keyboard.type(f'echo ZENIT_SWITCH_{index}');page.keyboard.press('Enter');page.wait_for_function('([id,marker])=>{const b=__qa.platform.terminals.get(id).xterm.buffer.active;return Array.from({length:b.length},(_,i)=>b.getLine(i)?.translateToString(true)).some(x=>x===marker);}',arg=[ids[index],f'ZENIT_SWITCH_{index}'],timeout=15000)
    page.locator('[data-terminal=terminal]').click();assert page.evaluate('__qa.platform.showingPTY');page.keyboard.type('echo ZENIT_TOOLBAR');page.keyboard.press('Enter');page.wait_for_function('(id)=>{const b=__qa.platform.terminals.get(id).xterm.buffer.active;return Array.from({length:b.length},(_,i)=>b.getLine(i)?.translateToString(true)).includes("ZENIT_TOOLBAR");}',arg=ids[0]);page.screenshot(path=str(out/'multiple-terminals.png'));passed('Switching terminals and clicking Terminal preserve input, selected PTY and separate buffers')
    child=browser.new_page(viewport={'width':1920,'height':1033});child.route('**/src/app.js',inject);child.on('pageerror',lambda e:errors.append(str(e)));child.goto(f'http://127.0.0.1:{server.server_port}?panel=project');child.wait_for_function('window.lumen?.ready');child.wait_for_function('document.querySelector(".native-window-heading")');geometry=child.evaluate('()=>{const p=document.querySelector("#project-panel"),h=p.querySelector(".native-window-heading"),t=p.querySelector(".sidebar-content");return {direction:getComputedStyle(p).flexDirection,heading:h.getBoundingClientRect().toJSON(),tree:t.getBoundingClientRect().toJSON(),overflow:document.documentElement.scrollWidth>innerWidth};}');assert geometry['direction']=='column',geometry;assert geometry['heading']['y']<30,geometry;assert geometry['tree']['y']>=geometry['heading']['bottom'],geometry;assert geometry['tree']['x']<40,geometry;assert not geometry['overflow'];child.screenshot(path=str(out/'project-detached.png'));child.close();passed('Detached Project has a top header and a full-width tree below it')
    page.evaluate('__qa.platform.useConsole();__qa.dock.show("assistant");__qa.dock.show("project")');page.locator('#ai-input').fill('Crea un proyecto Python con README y pruebas y borra el archivo old.py');page.locator('#ai-form .send-button').click();expect(page.locator('#confirm-yes')).to_be_visible();page.locator('#confirm-yes').click();button=page.locator('.chat-message.assistant button').filter(has_text='Revisar 4 archivos');expect(button).to_be_visible(timeout=15000);assert not (ws/'sample').exists();assert (ws/'old.py').exists();passed('Melody returns a complete reviewable plan without changing disk (fixture transport)')
    button.click();expect(page.locator('.melody-plan-files details')).to_have_count(4);page.screenshot(path=str(out/'melody-file-review.png'));page.locator('#melody-plan-apply').click();expect(page.locator('.chat-message.assistant')).to_contain_text('Aplicados 4 cambios');page.wait_for_function('window.lumen.activeFile==="sample/src/main.py"');assert (ws/'sample/src/main.py').read_text()=='print(42)\n';assert (ws/'sample/test_main.py').exists();assert not (ws/'old.py').exists();passed('Applying the reviewed project creates three real files and backs up the explicitly requested deletion')
    page.locator('.chat-message.assistant button').filter(has_text='Deshacer este plan').click();expect(page.locator('.chat-message.assistant')).to_contain_text('Plan deshecho');assert (ws/'old.py').read_text()=='print("old")\n';assert not (ws/'sample').exists();passed('Undo restores deleted content and removes unmodified created project files')
    assert not errors,errors;passed('No uncaught JavaScript errors');browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'projectGeometry':geometry,'aiTransport':'Explicit deterministic fixture; generation quality not measured.'},indent=2),encoding='utf-8')
if __name__=='__main__':main()





