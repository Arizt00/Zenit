"""Browser integration uses the real editor buffer, compiler and CPU worker."""
import argparse,json,tempfile,threading,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
 errors=[];checks=[]
 with tempfile.TemporaryDirectory(prefix='zenit-lab-') as temp:
  root=Path(temp);ws=root/'project';ws.mkdir();(ws/'example.s').write_text('.intel_syntax noprefix\n.text\nmov rax, 7\nadd rax, 5\nmov rbx, rax\n')
  app=Application(ROOT,ws,data_dir=root/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'updates.automatic':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1700,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
    page.locator('[data-file="example.s"]').click();page.locator('.foundation-toggle').click();expect(page.locator('.lab-tools article')).to_have_count(13);expect(page.locator('.lab-heading')).to_contain_text('Tu entorno, en orden.');checks.append('Real SDK inventory shown in separate sections');expect(page.locator('[data-lab-tools=languages] article:visible')).to_have_count(8);page.locator('.lab-filter input').fill('python');expect(page.locator('[data-lab-tools=languages] article:visible')).to_have_count(1);page.locator('.lab-filter input').fill('');page.evaluate('window.__labForm=document.querySelector("#lab-ssh");window.__labRoot=document.querySelector(".foundation-page")');page.locator('[data-lab-section=languages]').focus();page.keyboard.press('End');expect(page.locator('[data-lab-section=machines]')).to_be_focused();page.keyboard.press('Home');expect(page.locator('[data-lab-section=languages]')).to_be_focused();checks.append('Tool filter and tab keyboard navigation work')
    page.locator('[data-lab-section=project]').click();page.locator('.lab-advanced summary').first.click();page.locator('#lab-standards [name=c]').select_option('c99');page.locator('#lab-standards button.secondary-button').click();page.wait_for_timeout(400);assert app.features.runtimes.config['languages']['c']['standard']=='c99';checks.append('C standard persisted without discarding other profiles')
    page.locator('[data-lab-section=machines]').click();page.get_by_text('Conectar macOS, Windows 7 o Arch por SSH',exact=True).click();page.locator('#lab-ssh [name=host]').fill('192.168.1.20');page.locator('#lab-ssh [name=user]').fill('zenit');page.locator('#lab-ssh button.secondary-button').click();expect(page.locator('.lab-machine-list article')).to_have_count(1);assert page.evaluate('window.__labForm===document.querySelector("#lab-ssh")&&window.__labRoot===document.querySelector(".foundation-page")');expect(page.locator('#lab-ssh [name=host]')).to_have_value('192.168.1.20');checks.append('SSH profile persisted without remounting or clearing its form');page.locator('[data-lab-section=project]').click();page.locator('[data-lab-action=maven]').click();page.wait_for_function('Array.from(document.querySelectorAll(".xterm-screen")).some(e=>e.offsetWidth>0)');expect(page.locator('.forge-dashboard')).to_be_hidden();checks.append('A real Laboratory Maven terminal opens without Forge');page.locator('.foundation-toggle').click();expect(page.locator('[data-lab-section=project]')).to_have_attribute('aria-selected','true')
    for theme in ['day','dark','forest']:
     page.evaluate('(t)=>document.documentElement.dataset.theme=t',theme)
     for width,height in [(1700,1000),(1366,768),(1280,720)]:
      page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100)
      bounds=page.locator('.foundation-page').bounding_box();assert bounds['x']+bounds['width']<=width+1
      assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
      page.screenshot(path=str(out/f'lab-{theme}-{width}.png'))
    checks.append('Laboratory layouts fit three widths and three themes')
    page.locator('[data-lab-section=assembly]').click();page.locator('#lab-assembly').click();expect(page.locator('#workspace-style')).to_have_value('assembly');expect(page.locator('.asm-heading')).to_be_visible();page.locator('[data-asm=step]').click();expect(page.locator('.asm-status')).to_contain_text('1 instrucciones',timeout=20000);expect(page.locator('.asm-grid dl')).to_contain_text('0x7');checks.append('Step executes the unsaved editor buffer')
    page.locator('[data-asm=run]').click();expect(page.locator('.asm-status')).to_contain_text('Finalizada',timeout=20000);expect(page.locator('.asm-grid dl')).to_contain_text('0xc');checks.append('Full simulation computes registers')
    page.evaluate('monaco.editor.getModels().find(m=>m.uri.path.endsWith("example.s")).setValue(".intel_syntax noprefix\\n.text\\nmov rax, 3\\nadd rax, 5\\n")');expect(page.locator('.asm-status')).to_have_count(0);page.locator('[data-asm=run]').click();expect(page.locator('.asm-grid dl')).to_contain_text('0x8',timeout=20000);assert 'mov rax, 7' in (ws/'example.s').read_text();checks.append('Editing invalidates results; disk source remains unchanged')
    page.screenshot(path=str(out/'assembly-forest.png'));assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8')
 print(json.dumps(checks))
if __name__=='__main__':main()
