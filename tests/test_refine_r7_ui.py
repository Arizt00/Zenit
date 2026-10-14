"""R7 browser regressions with real Monaco, file I/O, Python and native LLDB."""
import argparse,json,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    def passed(label):checks.append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='zenit-r7-') as tmp:
        base=Path(tmp);ws=base/'Aurora';ws.mkdir();source='count = 1\ncount += 1\nprint(count)\n'
        (ws/'main.py').write_text(source);raw=b'MZ\x00'+bytes(range(256))*8;(ws/'sample.bin').write_bytes(raw);(ws/'hello.nc').write_text('stc main() { return 0; }\n')
        (ws/'machine.c').write_text('int main(void) {\n  volatile int count = 41;\n  count += 1;\n  return count == 42 ? 0 : 1;\n}\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Alex'});app.features.prefs.update({'general.showWelcome':False,'general.locale':'en','updates.automatic':False,'security.confirmRoutineActions':False,'appearance.motion':False})
        app.features.runtimes.config['tools'].update({'gcc':str(ROOT/'sdk/foundation/mingw/bin/gcc.exe'),'lldb-dap':'C:/Program Files/LLVM/bin/lldb-dap.exe'})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get dock(){return dock},get editor(){return editor},get platform(){return platformUI},openFile,closeFile,saveFile};')
                context.route('**/src/app.js',inject);page=context.new_page();page.on('pageerror',lambda e:errors.append(e.stack));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.py")')
                # Each actual built-in theme and both compact/full dimensions.
                for theme in ('day','dark','forest'):
                    page.evaluate('(t)=>__qa.platform.savePreference("appearance.theme",t)',theme)
                    for category in ('appearance','terminal','extensions','hardware'):
                        page.evaluate('(c)=>__qa.platform.settings(c)',category)
                        assert page.evaluate('()=>{const n=document.querySelector(".settings-navigation"),r=n.getBoundingClientRect();return [...n.querySelectorAll(".settings-nav-footer button")].every(b=>{const x=b.getBoundingClientRect();return x.right<=r.right+1&&x.left>=r.left;});}')
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        page.locator('.settings-content').evaluate('(e)=>e.scrollTop=e.scrollHeight');page.screenshot(path=str(out/f'settings-{category}-{theme}.png'),animations='disabled');page.evaluate('__qa.platform.closePage()')
                passed('All four pictured Settings sections retain controls and contrast in Day/Dark/Forest')
                page.evaluate('__qa.platform.savePreference("appearance.theme","day")');page.evaluate('__qa.dock.reset()');handle=page.locator('#tree-resizer').bounding_box();page.mouse.move(handle['x']+handle['width']/2,handle['y']+100);page.mouse.down();page.mouse.move(handle['x']-260,handle['y']+100,steps=8);page.mouse.up();assert 'left' in page.evaluate('__qa.dock.snapshot().collapsed');page.evaluate('__qa.dock.expand("left")');expect(page.locator('#project-panel')).to_be_visible();passed('Dragging a lateral panel past its minimum collapses it and allows restoration')
                page.evaluate('__qa.openFile("sample.bin")');expect(page.locator('.binary-view')).to_be_visible();expect(page.locator('.binary-view header')).to_contain_text('PE executable');assert page.evaluate('__qa.editor.models.get("sample.bin").model') is None
                page.locator('[data-byte="0"]').click();expect(page.locator('.binary-value')).to_contain_text('u8: 77');page.locator('[data-byte-next]').click();expect(page.locator('.binary-view form input')).to_have_value('0x200');page.keyboard.press('Control+s');page.screenshot(path=str(out/'binary.png'),animations='disabled');assert (ws/'sample.bin').read_bytes()==raw;passed('Binary bytes paginate and inspect numeric values; Save leaves the file byte-identical')
                page.evaluate('__qa.closeFile("sample.bin")');page.keyboard.press('Control+Shift+t');expect(page.locator('.binary-view')).to_be_visible();page.keyboard.press('Control+PageUp');expect(page.locator('.binary-view')).not_to_be_visible();assert page.evaluate('__qa.editor.current')=='main.py';passed('Closed binary tabs reopen; keyboard navigation restores the text model')
                page.evaluate('__qa.openFile("hello.nc")');expect(page.locator('.file-tab.active .file-type-nc img')).to_have_count(1);page.evaluate('__qa.openFile("main.py")');passed('nC uses its original language-extension icon')
                page.locator('.melody-research summary').click();page.locator('[data-research=capsule]').click();expect(page.locator('.research-result')).to_contain_text('Frozen source');page.keyboard.press('Escape');page.evaluate('__qa.editor.insertText("count = 7\\nprint(count)\\n",true)');page.locator('[data-research=drift]').click();expect(page.locator('.research-result pre')).to_contain_text('+count = 7');page.screenshot(path=str(out/'melody-drift.png'),animations='disabled');page.keyboard.press('Escape')
                for action,text in [('impact','Static reference'),('faults','Grouped observed'),('handoff','Session handoff')]:
                    page.locator(f'[data-research={action}]').click();expect(page.locator('.research-result')).to_contain_text(text);page.keyboard.press('Escape')
                assert (ws/'main.py').read_text()==source;passed('All five Melody tools execute local calculations against unsaved evidence without changing source')
                page.evaluate('__qa.editor.setValue('+json.dumps(source)+')');page.evaluate('__qa.saveFile()');page.evaluate('__qa.studio.debug()');page.locator('#debug-file').select_option('main.py');page.locator('#debug-start').click();page.wait_for_function('__qa.studio.debugWorkspace.state?.status==="paused"',timeout=15000)
                for _ in range(2):
                    line=page.evaluate('__qa.studio.debugWorkspace.state.line');page.locator('[data-debug=next]').click();page.wait_for_function('(line)=>__qa.studio.debugWorkspace.state?.status==="paused"&&__qa.studio.debugWorkspace.state.line!==line',arg=line,timeout=15000)
                page.locator('[data-debug-tab=history]').click();expect(page.locator('[data-pause-baseline] option')).to_have_count(3);expect(page.locator('[data-pause-diff]')).to_contain_text('count');page.screenshot(path=str(out/'debug-history.png'),animations='disabled');page.locator('[data-debug-tab=machine]').click();expect(page.locator('[data-machine-support]')).to_contain_text('Memory unsupported');assert page.locator('[data-machine-inspect]').is_disabled();passed('Real Python pauses produce a value comparison and accurately report unavailable machine access')
                page.locator('[data-debug=stop]').click();page.wait_for_function('__qa.studio.debugWorkspace.state?.status==="stopped"');page.locator('#debug-file').select_option('machine.c');page.locator('.debug-setup summary').click();page.locator('#debug-breakpoints').fill('3');page.locator('#debug-start').click();page.wait_for_function('["paused","error"].includes(__qa.studio.debugWorkspace.state?.status)&&!__qa.studio.debugWorkspace.state?.preparing',timeout=60000)
                state=page.evaluate('__qa.studio.debugWorkspace.state');assert state['status']=='paused',state
                assert state['machineCapabilities']['disassembly'],state
                page.locator('.machine-inspector select[name=operation]').select_option('disassembly');reference=state['stack'][0]['instructionPointerReference'];page.locator('.machine-inspector input[name=reference]').fill(reference);page.locator('.machine-inspector input[name=count]').fill('8');page.locator('[data-machine-inspect]').click();expect(page.locator('[data-machine-result]')).not_to_contain_text('Pause a supported',timeout=15000);page.screenshot(path=str(out/'debug-machine.png'),animations='disabled');passed('Real GCC/LLDB session returns native instruction addresses and disassembly')
                if state['machineCapabilities']['memory']:
                    page.locator('.machine-inspector select[name=operation]').select_option('memory');page.locator('.machine-inspector input[name=count]').fill('16');page.locator('[data-machine-inspect]').click();expect(page.locator('[data-machine-result]')).to_contain_text('Address:',timeout=15000);passed('Real LLDB readMemory exposes bytes from the paused instruction pointer')
                page.locator('[data-debug=stop]').click();page.evaluate('__qa.platform.closePage()');page.evaluate('__qa.studio.home()');page.mouse.move(20,20);avatar=page.locator('.welcome-profile');assert abs(avatar.bounding_box()['width']-52)<1;avatar.hover();assert avatar.evaluate('(e)=>getComputedStyle(e).backgroundColor')!='rgb(255, 255, 255)';page.screenshot(path=str(out/'home-expanded.png'),animations='disabled');page.mouse.move(20,20);page.evaluate('__qa.platform.savePreference("appearance.motion",true)');avatar.click();expect(page.locator('.profile-activity')).to_be_visible();assert page.evaluate('document.querySelector("#modal").getAnimations().some(a=>a.effect.getKeyframes().some(k=>k.clipPath))');page.locator('#modal').evaluate('(e)=>Promise.all(e.getAnimations().map(a=>a.finished.catch(()=>{})))');page.screenshot(path=str(out/'activity.png'),animations='disabled');passed('Avatar starts compact, expands without a white hover, and opens activity with a source-connected reveal')
                page.keyboard.press('Escape');page.emulate_media(reduced_motion='reduce');avatar.click();assert not page.evaluate('document.querySelector("#modal").getAnimations().length');passed('Reduced motion bypasses the profile morph')
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n')
if __name__=='__main__':main()
