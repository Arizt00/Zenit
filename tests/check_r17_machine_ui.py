import json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 out=ROOT/'qa-output/r17-machine-ui';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-r17-machine-ui-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'main.c').write_text('int marker=42;\nint main(void){\n int answer=marker+1;\n answer+=2;\n return answer==45?0:1;\n}\n');app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False});debug=app.features.debugger;debug.start(app.workspace,'main.c',[4]);deadline=time.monotonic()+60
  try:
   while time.monotonic()<deadline:
    state=debug.snapshot()
    if state['status'] in ('paused','error'):break
    time.sleep(.05)
   assert state['status']=='paused',state;binary=next((ws/'build').rglob('*.exe'));relative=binary.relative_to(ws).as_posix();copy=ws/'previous.exe';data=binary.read_bytes();copy.write_bytes(data[:500]+bytes([data[500]^1])+data[501:]);server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
   try:
    with sync_playwright() as pw:
     browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
     def inject(route):
      response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},openFile};')
     page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.platformReady');page.evaluate('(path)=>__qa.openFile(path)',relative);page.locator('.binary-structure>summary').click();page.locator('[data-binary-inspect]').click();expect(page.locator('[data-binary-structure]')).to_contain_text('PE32+');expect(page.locator('[data-binary-structure]')).to_contain_text('.text');expect(page.locator('[data-binary-structure]')).to_contain_text('marker');page.locator('[data-binary-compare] input').fill('previous.exe');page.locator('[data-binary-compare] button:not([type=button])').click();expect(page.locator('[data-binary-comparison]')).to_contain_text('1 bytes distintos');page.screenshot(path=str(out/'binary-structure.png'));checks.append('Real PE sections/symbols and a one-byte version difference appear in the binary editor')
     page.evaluate('__qa.studio.debug()');page.locator('[data-debug-tab=machine]').click();expect(page.locator('.machine-registers>div').first).to_be_visible();page.locator('[data-machine-sync]').click();expect(page.locator('[data-machine-disassembly]')).not_to_contain_text('Sincroniza');expect(page.locator('[data-machine-disassembly]')).to_contain_text('0x');expect(page.locator('[data-machine-memory]')).not_to_be_empty();assert page.locator('[data-machine-back]').is_disabled();page.screenshot(path=str(out/'native-machine.png'));checks.append('Actual paused process shows registers, synchronized memory/disassembly and unavailable reverse control')
     assert not errors,errors;browser.close()
   finally:server.shutdown();server.server_close()
  finally:app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8');print('PASS',checks)
if __name__=='__main__':main()
