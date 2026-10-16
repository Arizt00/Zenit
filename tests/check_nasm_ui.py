"""Real Linux/Windows NASM simulation through the visible workbench controls."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.nasm import EXAMPLES
from playwright.sync_api import sync_playwright,expect

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
 def passed(text):checks.append(text);print('PASS',text,flush=True)
 with tempfile.TemporaryDirectory(prefix='zenit-nasm-ui-',ignore_cleanup_errors=True) as tmp:
  base=Path(tmp);ws=base/'Assembly';ws.mkdir()
  files={'linux.asm':EXAMPLES['linux']['x86_64'],'windows.asm':EXAMPLES['windows']['x86_64'],'windows32.asm':EXAMPLES['windows']['x86'],'broken.asm':'global _start\nsection .text\n_start:\ninvalid_instruction eax,1\n'}
  for name,code in files.items():(ws/name).write_text(code,encoding='utf-8')
  app=Application(args.root,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'workspaceStyle':'assembly'});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get profiles(){return workspaceProfiles},openFile};')
    page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready')
    page.evaluate('__qa.openFile("linux.asm")');page.wait_for_function('__qa.profiles.assembly?.catalog')
    def field(name):return page.locator('select[aria-label="'+name+'"]')
    expect(field('Motor ASM')).to_have_value('nasm');expect(field('Sistema NASM')).to_have_value('linux')
    page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('Finalizada');expect(page.locator('.asm-status')).to_contain_text('salida 8');expect(page.locator('.asm-status')).to_contain_text('elf64')
    assert page.evaluate('__qa.profiles.assembly.result.registers.rdi')=='0x8';assert page.evaluate('__qa.editor.getValue()')==files['linux.asm']
    page.mouse.move(40,80);expect(page.locator('[data-asm="run"]')).to_be_enabled();page.wait_for_timeout(250);page.screenshot(path=str(out/'nasm-linux.png'));passed('NASM and Linux are detected automatically; real ELF64 simulation exits with 8 and preserves the buffer')
    page.locator('[data-asm="reset"]').click();page.locator('[data-asm="step"]').click();expect(page.locator('.asm-status')).to_contain_text('En pausa');expect(page.locator('.asm-status')).to_contain_text('1 instrucciones');assert page.evaluate('__qa.profiles.assembly.result.registers.rax')=='0x5';passed('Single stepping runs exactly one NASM instruction')
    page.evaluate('__qa.openFile("windows.asm")');expect(field('Sistema NASM')).to_have_value('windows');page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('win64');expect(page.locator('.asm-status')).to_contain_text('salida 8');page.screenshot(path=str(out/'nasm-windows.png'));passed('Windows target assembles COFF, links a real PE image and returns 8 from main')
    page.evaluate('__qa.openFile("windows32.asm")');expect(field('Arquitectura ASM')).to_have_value('x86');page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('win32');expect(page.locator('.asm-status')).to_contain_text('salida 8');passed('BITS 32 chooses x86 and executes a real PE32 image')
    page.evaluate('__qa.openFile("windows.asm")');field('Sistema NASM').select_option('linux');expect(page.locator('.asm-status')).to_have_count(0);page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('elf64');page.evaluate('__qa.openFile("linux.asm")');page.evaluate('__qa.openFile("windows.asm")');expect(field('Sistema NASM')).to_have_value('linux');passed('Explicit target choices survive file switching and invalidate results from the previous target')
    field('Motor ASM').select_option('llvm');page.evaluate('__qa.profiles.paint()');expect(field('Motor ASM')).to_have_value('llvm');field('Motor ASM').select_option('nasm');passed('A manual engine selection is preserved when the workbench repaints')
    page.evaluate('__qa.openFile("linux.asm")');page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('salida 8');page.set_viewport_size({'width':1100,'height':760});page.screenshot(path=str(out/'nasm-compact.png'))
    assert page.locator('.asm-controls').evaluate('e=>{const r=e.getBoundingClientRect();return [...e.children].filter(n=>getComputedStyle(n).display!=="none").every(n=>{const b=n.getBoundingClientRect();return b.left>=r.left-1&&b.right<=r.right+1})}')
    passed('NASM controls wrap inside the laboratory at a compact window size')
    page.evaluate('__qa.openFile("broken.asm")');page.locator('[data-asm="run"]').click();expect(page.locator('.lab-error')).to_contain_text('buffer.asm:4');passed('Invalid source reports the NASM filename and exact line')
    for name,code in files.items():assert (ws/name).read_text(encoding='utf-8')==code
    assert not (ws/'CMakeLists.txt').exists();browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8');assert not errors,errors
if __name__=='__main__':main()
