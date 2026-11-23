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
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get profiles(){return workspaceProfiles},get desktop(){return desktopUI},get platform(){return platformUI},openFile};')
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
    starts=[];simulations=[]
    page.on('request',lambda r:starts.append(r.url) if '/hacker/start' in r.url else simulations.append(r.url) if '/simulation/run' in r.url else None)
    page.set_viewport_size({'width':1600,'height':1000});page.evaluate('__qa.openFile("windows.asm")');field('Sistema NASM').select_option('windows');field('Destino de ejecución ASM').select_option('native')
    expect(page.locator('[data-asm="step"]')).to_be_disabled();expect(page.locator('.asm-native-mode')).to_contain_text('Máquina real');page.locator('[data-asm="run"]').click()
    page.wait_for_function('__qa.platform.terminals.get(__qa.desktop.forgeRun?.terminal)?.closed',timeout=30000)
    assert page.evaluate('__qa.platform.terminals.get(__qa.desktop.forgeRun.terminal).code')==8
    assert len(starts)==1 and len(simulations)==0,(starts,simulations)
    page.mouse.move(40,80);expect(page.locator('[data-asm="run"]')).to_be_enabled();page.wait_for_timeout(650);page.screenshot(path=str(out/'nasm-native.png'));passed('Machine mode builds and executes a real Windows process once, exits with 8 and never calls the simulator')
    page.evaluate('__qa.openFile("linux.asm")');page.locator('[data-asm="run"]').click();expect(page.locator('.toast').last).to_contain_text('WSL');assert len(starts)==1 and not simulations
    field('Destino de ejecución ASM').select_option('simulation');page.locator('[data-asm="run"]').click();expect(page.locator('.asm-status')).to_contain_text('salida 8');assert len(simulations)==1
    passed('Linux ABI is refused on a real Windows host; switching back to simulation executes the same unchanged buffer')
    # The original CLI file may have been removed after the main app started.
    # A child must use its URL and shared text, rather than replay that stale path.
    app.startup={'path':'deleted-original.s'}
    changed=files['linux.asm'].replace('mov rax, 5','mov rax, 7')
    assert changed!=files['linux.asm']
    page.evaluate('(text)=>__qa.editor.insertText(text,true)',changed)
    with page.expect_popup() as popup:page.evaluate('__qa.desktop.detach("profile-assembly","linux.asm")')
    child=popup.value;child.route('**/src/app.js',inject);child.on('pageerror',lambda e:errors.append(str(e)));child.wait_for_function('window.lumen?.ready')
    # The popup can request its module before the page-specific route is ready.
    if not child.evaluate('!!window.__qa'):child.reload();child.wait_for_function('window.lumen?.ready')
    assert child.evaluate('__qa.editor.current')=='linux.asm';assert child.evaluate('__qa.editor.getValue()')==changed;assert child.evaluate('__qa.editor.isDirty()')
    child.locator('[data-asm="run"]').click();expect(child.locator('.asm-status')).to_contain_text('salida 10');assert (ws/'linux.asm').read_text(encoding='utf-8')==files['linux.asm']
    child.screenshot(path=str(out/'nasm-detached.png'));child.close();passed('Detached laboratory ignores a deleted original startup file and simulates the latest unsaved shared buffer')
    page.evaluate('__qa.openFile("windows32.asm")');page.evaluate('__qa.desktop.share("windows32.asm")');(ws/'windows32.asm').unlink()
    with page.expect_popup() as popup:page.evaluate('__qa.desktop.detach("profile-assembly","windows32.asm")')
    child=popup.value;child.route('**/src/app.js',inject);child.on('pageerror',lambda e:errors.append(str(e)));child.wait_for_function('window.lumen?.ready')
    if not child.evaluate('!!window.__qa'):child.reload();child.wait_for_function('window.lumen?.ready')
    assert child.evaluate('__qa.editor.isDirty()');child.locator('[data-asm="run"]').click();expect(child.locator('.asm-status')).to_contain_text('salida 8');assert not (ws/'windows32.asm').exists();child.close()
    (ws/'windows32.asm').write_text(files['windows32.asm'],encoding='utf-8');passed('An open shared buffer remains available in a detached laboratory even when its disk file was removed')
    for name,code in files.items():assert (ws/name).read_text(encoding='utf-8')==code
    assert not (ws/'CMakeLists.txt').exists();browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2),encoding='utf-8');assert not errors,errors
if __name__=='__main__':main()
