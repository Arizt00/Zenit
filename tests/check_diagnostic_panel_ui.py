"""Real compiler diagnostics, hover geometry and Lens values in disposable projects."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.server import Application, LumenServer
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT, help='Source or installed resource root')
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    checks, errors, geometry = [], [], []

    def passed(label):
        checks.append(label)
        print('PASS', label, flush=True)

    with tempfile.TemporaryDirectory(prefix='zenit-diagnostic-panel-', ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        ws = base / 'Compiler'
        ws.mkdir()
        source = '#include <stdio.h>\n\nint main(void) {\n    int a = 3;\n    int b = 5;\n    int resulado = a + b;\n    printf("%d\\n", resultado);\n    return 0;\n}\n'
        (ws / 'example.c').write_text(source, encoding='utf-8')
        (ws / 'values.py').write_text('answer = 6 * 7\nprint(answer)\n', encoding='utf-8')
        app = Application(args.root, ws, data_dir=base / 'profile')
        app.workspace.trusted = True
        app.features.studio.update({'onboarded': True})
        app.features.prefs.update({'general.locale': 'es', 'general.showWelcome': False,
                                  'updates.automatic': False, 'security.confirmRoutineActions': False,
                                  'appearance.motion': True})
        server = LumenServer(0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1600, 'height': 1000})
                page.on('pageerror', lambda e: errors.append(str(e)))

                def inject(route):
                    response = route.fetch()
                    route.fulfill(response=response, body=response.text() +
                                  '\nwindow.__qa={get editor(){return editor},get dock(){return dock},get preview(){return previewUI},get platform(){return platformUI},get studio(){return studio},openFile};')

                page.route('**/src/app.js', inject)
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.wait_for_function('window.lumen?.ready')
                page.evaluate('__qa.openFile("example.c")')
                # Actual clicks reproduce the two competing tab-menu handlers.
                pop = page.locator('#popover')
                page.locator('.tree-row[data-file="example.c"]').click()
                expect(pop).to_be_hidden()
                page.locator('.tree-row[data-file="example.c"]').click(button="right")
                expect(pop).to_be_visible()
                expect(pop.get_by_role('menuitem', name='Guardar', exact=True)).to_be_visible()
                expect(pop.get_by_role('menuitem', name='Guardar como…', exact=True)).to_be_visible()
                page.wait_for_timeout(350)
                expect(pop).to_be_visible()
                page.keyboard.press('Escape')
                page.evaluate('__qa.editor.view.setValue(__qa.editor.getValue()+"\\n// Saved from explorer\\n")')
                edited = page.evaluate('__qa.editor.getValue()')
                page.locator('.tree-row[data-file="example.c"]').click(button='right')
                pop.get_by_role('menuitem', name='Guardar', exact=True).click()
                page.wait_for_function('!__qa.editor.isDirty("example.c")')
                assert (ws / 'example.c').read_text(encoding='utf-8') == edited
                page.locator('.tree-row[data-file="example.c"]').click(button="right")
                pop.get_by_role('menuitem', name='Guardar como…', exact=True).click()
                expect(page.locator('#save-as-form')).to_be_visible()
                page.locator('#save-as-path').fill('saved-copy.c')
                page.locator('#save-as-form').get_by_role('button', name='Guardar copia').click()
                page.wait_for_function('__qa.editor.current === "saved-copy.c"')
                assert (ws / 'saved-copy.c').read_text(encoding='utf-8') == edited
                assert (ws / 'example.c').read_text(encoding='utf-8') == edited
                for attempt in range(2):
                    page.locator('.file-tab[data-tab="example.c"]').click()
                    expect(pop).to_be_hidden()
                    page.locator('.file-tab[data-tab="example.c"]').click(button='right')
                    expect(pop).to_be_visible()
                    expect(pop.get_by_role('menuitem', name='Guardar', exact=True)).to_be_visible()
                    expect(pop.get_by_role('menuitem', name='Reabrir pestaña cerrada', exact=True)).to_be_visible()
                    page.wait_for_timeout(350)
                    expect(pop).to_be_visible()
                    page.keyboard.press('Escape')
                page.evaluate('__qa.openFile("example.c")')
                page.evaluate('(text)=>__qa.editor.view.setValue(text)', source)
                page.evaluate('__qa.preview.host.saveFile("example.c")')
                passed('Right click keeps file menus open and left click only opens the file; explorer Save and Save As preserve the original')
                page.evaluate('__qa.studio.lantern.action("start")')
                page.wait_for_function('monaco.editor.getModelMarkers({resource:__qa.editor.view.getModel().uri}).some(m=>m.severity===8)', timeout=30000)
                page.evaluate('__qa.studio.lantern.action("close-inline")')
                expect(page.locator('.lantern-lens-error')).to_have_count(0)
                assert page.evaluate('__qa.editor.getValue()') == source
                assert (ws / 'example.c').read_text(encoding='utf-8') == source
                passed('A real C compiler error stays a marker without inserting its description into code or changing the file')

                def show_marker(line=7, column=20):
                    page.mouse.move(20, 80)
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(350)
                    page.evaluate('(p)=>{__qa.editor.view.focus();__qa.editor.view.revealPositionInCenterIfOutsideViewport(p);__qa.editor.view.setPosition(p)}', {'lineNumber': line, 'column': column})
                    position = page.evaluate('(p)=>{const v=__qa.editor.view,r=v.getDomNode().getBoundingClientRect(),s=v.getScrolledVisiblePosition(p);return {x:r.x+s.left+2,y:r.y+s.top+s.height/2,bottom:r.y+s.top+s.height}}', {'lineNumber': line, 'column': column})
                    page.mouse.move(position['x'], position['y'])
                    panel = page.locator('.zenit-diagnostic-panel:visible')
                    expect(panel).to_be_visible()
                    expect(panel).to_have_css('opacity', '1')
                    return panel, position

                for theme in ('day', 'dark', 'forest'):
                    page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)', theme)
                    panel, position = show_marker()
                    expect(panel).to_contain_text('resultado')
                    expect(panel.locator('.diagnostic-file')).to_contain_text('example.c')
                    expect(panel).to_have_attribute('data-severity', 'error')
                    box = panel.bounding_box()
                    assert box['y'] >= position['bottom'] - 1, (theme, box, position)
                    assert 300 <= box['width'] <= 390 and 76 <= box['height'] <= 365, box
                    material = panel.evaluate('e=>{const s=getComputedStyle(e);return {background:s.backgroundColor,opacity:s.opacity,filter:s.backdropFilter}}')
                    assert material['opacity'] == '1', material
                    alpha = page.evaluate('(color)=>{const ctx=document.createElement("canvas").getContext("2d");ctx.fillStyle=color;ctx.fillRect(0,0,1,1);return ctx.getImageData(0,0,1,1).data[3]/255}', material['background'])
                    assert abs(alpha - .65) < .01, material
                    assert panel.evaluate('e=>[e,...e.querySelectorAll("*")].every(n=>n.scrollWidth<=n.clientWidth+1&&n.scrollHeight<=n.clientHeight+1)')
                    page.screenshot(path=str(out / f'diagnostic-{theme}.png'))
                    geometry.append({'theme': theme, 'panel': box, 'anchor': position, 'material': material})
                passed('Descriptions open below the error, wrap inside a moderate rectangle and retain 35% material transparency in every theme')

                page.mouse.move(box['x'] + 30, box['y'] + 25)
                expect(panel).to_be_visible()
                page.keyboard.press('Escape')
                expect(panel).to_be_hidden()
                page.evaluate('__qa.editor.view.focus();__qa.editor.view.setPosition({lineNumber:7,column:20});__qa.editor.view.getAction("zenit.diagnostic.show").run()')
                expect(panel).to_be_visible()
                page.keyboard.press('Escape')
                passed('Pointer entry keeps the panel readable; Escape closes it and the editor hover action also opens it from the keyboard')

                selection = page.evaluate('__qa.editor.view.setSelection(new monaco.Range(6,5,7,32));__qa.editor.getSelection()')
                for placement in ('right', 'left', 'bottom'):
                    page.evaluate('(side)=>__qa.dock.move("assistant",side)', placement)
                    page.evaluate('__qa.preview.contextMenu.open(__qa.editor.view,600,350)')
                    page.locator('.editor-context-menu:not(.menu-leaving)').get_by_role('menuitem', name='Melody', exact=True).click()
                    page.locator('.editor-context-menu:not(.menu-leaving)').get_by_role('menuitem', name='Explicar selección o archivo', exact=True).click()
                    expect(page.locator('#ai-input')).to_be_focused()
                    assert page.evaluate('__qa.dock.snapshot().floating.assistant||null') is None
                    assert page.evaluate('(side)=>__qa.dock.snapshot().groups[side].includes("assistant")', placement)
                    assert page.evaluate('__qa.editor.getSelection()') == selection
                page.evaluate('__qa.dock.hide("assistant")')
                page.evaluate('__qa.preview.contextMenu.items(__qa.editor.view).find(x=>x.label==="Melody").children[0].run()')
                assert page.evaluate('__qa.dock.isVisible("assistant")')
                assert page.evaluate('__qa.dock.snapshot().floating.assistant||null') is None
                page.evaluate('__qa.dock.floatPanel("assistant")')
                before = page.evaluate('__qa.dock.snapshot().floating.assistant')
                page.evaluate('__qa.preview.contextMenu.items(__qa.editor.view).find(x=>x.label==="Melody").children[0].run()')
                assert page.evaluate('__qa.dock.snapshot().floating.assistant') == before
                page.evaluate('__qa.dock.move("assistant","right")')
                passed('Explain selection preserves its text and Melody placement at right, left, bottom, hidden and deliberately floating')

                page.evaluate('__qa.studio.lantern.action("stop")')
                page.evaluate('for(const owner of new Set(monaco.editor.getModelMarkers({resource:__qa.editor.view.getModel().uri}).map(m=>m.owner)))monaco.editor.setModelMarkers(__qa.editor.view.getModel(),owner,[])')
                # A stationary pointer must follow asynchronous language-server updates.
                page.mouse.move(20,80)
                page.keyboard.press('Escape')
                page.wait_for_timeout(350)
                anchor=page.evaluate('()=>{const v=__qa.editor.view,r=v.getDomNode().getBoundingClientRect(),p=v.getScrolledVisiblePosition({lineNumber:7,column:20});return {x:r.x+p.left+2,y:r.y+p.top+p.height/2}}')
                page.mouse.move(anchor['x'],anchor['y'])
                page.wait_for_timeout(400)
                expect(page.locator('.zenit-diagnostic-panel:visible')).to_have_count(0)
                page.evaluate('__qa.editor.setDiagnostics("example.c",[{startLineNumber:7,startColumn:20,endColumn:29,severity:8,message:"Late analyzer diagnostic"}],"qa-stationary")')
                late=page.locator('.zenit-diagnostic-panel:visible')
                expect(late).to_contain_text('Late analyzer diagnostic')
                assert page.evaluate('async()=>{const m=__qa.editor.view.getModel();monaco.editor.setModelMarkers(m,"qa-stationary",[]);await new Promise(r=>setTimeout(r,60));const stayed=!__qa.editor.diagnosticPanels.node.hidden;monaco.editor.setModelMarkers(m,"qa-stationary",[{startLineNumber:7,startColumn:20,endLineNumber:7,endColumn:29,severity:8,message:"Refreshed analyzer diagnostic"}]);return stayed}')
                expect(late).to_contain_text('Refreshed analyzer diagnostic')
                page.keyboard.press('Escape')
                page.evaluate('monaco.editor.setModelMarkers(__qa.editor.view.getModel(),"qa-stationary",[])')
                page.wait_for_timeout(400)
                expect(late).to_have_count(0)
                passed('Stationary hover follows late diagnostics and analyzer refresh without blinking, and respects Escape')
                page.evaluate('__qa.editor.setDiagnostics("example.c",[{startLineNumber:7,startColumn:20,endColumn:29,severity:8,message:"<img src=x onerror=alert(1)> " + "An extended diagnostic description with additional context. ".repeat(70)}],"qa-long")')
                panel, _ = show_marker()
                expect(panel).to_contain_text('<img src=x onerror=alert(1)>')
                expect(panel.locator('img')).to_have_count(0)
                long_box = panel.bounding_box()
                assert long_box['width'] <= 390 and long_box['height'] <= 365, long_box
                seen=[]
                while True:
                    seen.append(panel.locator('.diagnostic-message').inner_text())
                    assert panel.evaluate('e=>[e,...e.querySelectorAll("*")].every(n=>n.scrollHeight<=n.clientHeight+1)')
                    if panel.locator('[data-diagnostic-next]').is_disabled():break
                    panel.locator('[data-diagnostic-next]').click(timeout=4000)
                    assert len(seen)<100
                assert ''.join(seen).startswith('<img src=x onerror=alert(1)> ')
                assert ''.join(seen).count('An extended diagnostic description with additional context.')==70
                page.screenshot(path=str(out / 'diagnostic-long.png'))
                passed('Long diagnostics use complete consecutive pages without scroll, clipping or HTML execution')

                page.keyboard.press('Escape')
                page.evaluate('__qa.editor.setDiagnostics("example.c",[{startLineNumber:7,startColumn:20,endColumn:29,severity:8,message:"First diagnostic",source:"Compiler"},{startLineNumber:7,startColumn:20,endColumn:29,severity:4,message:"Second diagnostic",source:"Language server"}],"qa-long")')
                panel, _ = show_marker()
                expect(panel.locator('.diagnostic-message')).to_have_text('First diagnostic')
                panel.locator('[data-diagnostic-next]').click()
                expect(panel.locator('.diagnostic-message')).to_have_text('Second diagnostic')
                expect(panel).to_have_attribute('data-severity','warning')
                page.keyboard.press('ArrowLeft')
                expect(panel.locator('.diagnostic-message')).to_have_text('First diagnostic')
                page.keyboard.press('Escape')
                page.emulate_media(reduced_motion='reduce')
                panel, _ = show_marker()
                assert panel.evaluate('e=>e.getAnimations({subtree:true}).length')==0
                page.keyboard.press('Escape')
                expect(panel).to_be_hidden()
                page.emulate_media(reduced_motion='no-preference')
                page.set_viewport_size({'width':1000,'height':700})
                panel, _ = show_marker()
                box=panel.bounding_box()
                assert box['x']>=12 and box['y']>=12 and box['x']+box['width']<=988 and box['y']+box['height']<=688,box
                page.screenshot(path=str(out/'diagnostic-compact.png'))
                passed('Multiple severities support pointer and keyboard paging; reduced motion has no animations and the compact viewport has no clipped card')

                page.keyboard.press('Escape')
                page.set_viewport_size({'width': 1000, 'height': 700})
                page.evaluate('__qa.openFile("values.py")')
                expect(panel).to_be_hidden()
                page.evaluate('__qa.studio.lantern.action("start")')
                page.wait_for_function('document.querySelector(".lantern-lens-value")?.textContent.includes("42")', timeout=30000)
                expect(page.locator('.lantern-lens-error')).to_have_count(0)
                assert page.evaluate('__qa.editor.getValue()') == 'answer = 6 * 7\nprint(answer)\n'
                page.screenshot(path=str(out / 'runtime-values.png'))
                passed('Switching files dismisses old errors while real Python runtime Lens values still appear')
                page.evaluate('__qa.studio.lantern.action("stop")')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            app.features.shutdown()
            app.runner.shutdown()
    (out / 'verification.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'geometry': geometry}, indent=2, ensure_ascii=False), encoding='utf-8')
    assert not errors, errors


if __name__ == '__main__':
    main()
