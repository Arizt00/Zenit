"""R16 geometry regression: narrow docks and binary controls in the actual UI."""
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
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks, failures, errors, samples = [], [], [], []
    with tempfile.TemporaryDirectory(prefix='zenit-r16-visual-', ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        workspace = base / 'Project'
        workspace.mkdir()
        (workspace / 'main.py').write_text('print("visual review")\n', encoding='utf-8')
        (workspace / 'sample.bin').write_bytes(bytes(range(256)) * 4)
        app = Application(args.root.resolve(), workspace, data_dir=base / 'profile')
        app.workspace.trusted = True
        app.features.studio.update({'onboarded': True, 'workspaceStyle': 'general'})
        app.features.prefs.update({'general.locale': 'es', 'general.showWelcome': False, 'updates.automatic': False, 'appearance.motion': False})
        server = LumenServer(0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=True)
                context = browser.new_context(viewport={'width': 1600, 'height': 1000})
                page = context.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))

                def inject(route):
                    response = route.fetch()
                    route.fulfill(response=response, body=response.text() + '\nwindow.__qa={get dock(){return dock},get platform(){return platformUI},get workbench(){return workbenchUI},get team(){return teamUI},openFile};')

                context.route('**/src/app.js', inject)
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.wait_for_function('window.lumen?.ready')
                page.evaluate('__qa.openFile("main.py")')
                for theme in ('day', 'dark', 'forest'):
                    page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)', theme)
                    for width, left, right in ((1600, 300, 360), (1366, 200, 260), (1100, 230, 230)):
                        page.set_viewport_size({'width': width, 'height': 900})
                        page.evaluate('([left,right])=>{__qa.dock.state.hidden=[];__qa.dock.state.collapsed=[];__qa.dock.state.sizes.left=left;__qa.dock.state.sizes.right=right;__qa.dock.render()}', [left, right])
                        page.wait_for_timeout(200)
                        geometry = page.evaluate('''()=>{
                          const rect=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
                          return {body:document.documentElement.scrollWidth,width:innerWidth,headers:['#project-panel>.panel-heading','.editor-tabbar','#assistant-panel>.assistant-heading'].map(s=>{const n=document.querySelector(s),r=rect(n),title=n.querySelector('h1,h2');return {s,...r,title:title?rect(title):null,buttons:[...n.querySelectorAll('button')].filter(b=>b.offsetWidth).map(b=>({label:b.getAttribute('aria-label')||b.title,...rect(b)}))}})};
                        }''')
                        label = f'{theme} {width}px, docks {left}/{right}'
                        samples.append({'case': label, 'geometry': geometry})
                        issues = []
                        if geometry['body'] > width + 1:
                            issues.append('document overflow')
                        for header in geometry['headers']:
                            if abs(header['height'] - 52) > 1:
                                issues.append(header['s'] + ': unequal header height ' + str(header['height']))
                            for button in header['buttons']:
                                if button['x'] < header['x'] - 1 or button['right'] > header['right'] + 1 or button['bottom'] > header['bottom'] + 1:
                                    issues.append(header['s'] + ': clipped ' + button['label'])
                                if header['title'] and button['x'] < header['title']['right'] - 1:
                                    issues.append(header['s'] + ': title overlaps ' + button['label'])
                        if issues:
                            failures.append({'case': label, 'issues': issues})
                        else:
                            checks.append(label + ': aligned headers and visible actions')
                        page.screenshot(path=str(args.output / f'{theme}-{width}-panels.png'))

                    page.set_viewport_size({'width': 1366, 'height': 900})
                    page.evaluate('__qa.dock.state.sizes.left=200;__qa.dock.render()')
                    menu = page.locator('#project-panel .zenit-tools-menu')
                    menu.click()
                    expect(page.get_by_role('menuitem', name='Nuevo archivo', exact=True)).to_be_visible()
                    expect(page.get_by_role('menuitem', name='Abrir Proyecto en el escritorio', exact=True)).to_be_visible()
                    menu.click()
                    expect(page.locator('#popover')).to_have_class('popover hidden')
                    checks.append(theme + ': narrow project actions stay available and the menu toggles closed')

                    page.set_viewport_size({'width': 1600, 'height': 1000})
                    page.evaluate('__qa.dock.hide("assistant");__qa.dock.state.sizes.left=270;__qa.dock.render();__qa.openFile("sample.bin")')
                    page.wait_for_selector('.binary-view')
                    geometry = page.evaluate('''()=>{const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};return {edit:box('.binary-edit-tools'),actions:box('.binary-action-tools'),table:box('.binary-scroll'),tools:box('.binary-tools'),view:box('.binary-view')}}''')
                    samples.append({'case': theme + ' wide binary', 'geometry': geometry})
                    if abs(geometry['edit']['y'] - geometry['actions']['y']) > 3:
                        failures.append({'case': theme + ' wide binary', 'issues': ['Editing and file actions occupy separate rows despite sufficient width']})
                    else:
                        checks.append(theme + ': compact binary toolbar')
                    page.screenshot(path=str(args.output / f'{theme}-binary.png'))
                    # The same controls must fit a split editor, independently of
                    # the viewport's media breakpoints.
                    page.evaluate('__qa.dock.show("assistant");__qa.dock.state.sizes.left=250;__qa.dock.state.sizes.right=360;__qa.dock.render()')
                    page.set_viewport_size({'width': 1100, 'height': 900})
                    page.wait_for_timeout(200)
                    overflow = page.evaluate('''()=>{const view=document.querySelector('.binary-view'),r=view.getBoundingClientRect();return [...view.querySelectorAll('button,input,textarea')].filter(n=>n.offsetWidth&&!n.closest('table')).map(n=>({label:n.getAttribute('aria-label')||n.textContent,x:n.getBoundingClientRect().x,right:n.getBoundingClientRect().right})).filter(n=>n.x<r.x-1||n.right>r.right+1)}''')
                    if overflow:
                        failures.append({'case': theme + ' narrow binary', 'issues': overflow})
                    else:
                        checks.append(theme + ': binary controls fit a narrow editor')
                    grid_height = page.locator('.binary-scroll').evaluate('n=>n.getBoundingClientRect().height')
                    if grid_height < 150:
                        failures.append({'case': theme + ' narrow binary', 'issues': ['Hexadecimal grid collapsed below a usable height']})
                    else:
                        checks.append(theme + ': narrow hexadecimal grid retains a usable height')
                    for label in ('Guardar', 'Recompilar', 'Ejecutar'):
                        expect(page.locator('.binary-action-tools').get_by_role('button', name=label, exact=True)).to_be_visible()
                    page.screenshot(path=str(args.output / f'{theme}-binary-narrow.png'))
                    page.evaluate('__qa.openFile("main.py")')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            app.features.shutdown()
    report = {'checks': checks, 'failures': failures, 'errors': errors, 'samples': samples}
    (args.output / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': len(checks), 'failures': failures, 'errors': errors}), flush=True)
    if errors or (failures and not args.baseline):
        raise AssertionError('Visual geometry regression; see verification.json')


if __name__ == '__main__':
    main()
