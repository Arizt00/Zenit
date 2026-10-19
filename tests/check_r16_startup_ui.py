"""Slow or failing optional discovery must never block the recovered editor."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-startup-qa-',ignore_cleanup_errors=True) as tmp:
        base=Path(tmp);workspace=base/'project';workspace.mkdir();(workspace/'main.py').write_text('print("restored")\n')
        app=Application(args.root,workspace,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'updates.automatic':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1500,'height':950});page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                pending={}
                def hold(route):pending[route.request.url.rsplit('/',1)[-1]]=route
                context.route('**/api/platform/extensions/contributions',hold);context.route('**/api/platform/hacker',hold)
                started=time.monotonic();page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded');page.wait_for_function('window.lumen?.ready',timeout=15000)
                checks.append('Editor opens while both extension contributions and optional tool discovery are still pending')
                page.locator('[data-file="main.py"]').click();page.wait_for_function('window.lumen.activeFile==="main.py"')
                expected='print(42)\n'
                page.wait_for_function('!!window.zenitSessionSnapshot');page.evaluate('(text)=>monaco.editor.getModels().find(m=>m.uri.path.endsWith("main.py")).setValue(text)',expected)
                expect(page.locator('#connection-overlay')).to_be_hidden();checks.append('The editor remains usable and accepts unsaved changes during pending discovery')
                while len(pending)<2:page.wait_for_timeout(50)
                pending.pop('hacker').fulfill(status=503,json={'error':'Optional discovery temporarily unavailable'})
                pending.pop('contributions').fulfill(status=503,json={'error':'Extension catalog temporarily unavailable'})
                expect(page.locator('.toast').filter(has_text='Extension catalog temporarily unavailable')).to_be_visible()
                expect(page.locator('#connection-overlay')).to_be_hidden();assert page.evaluate('window.lumen.ready');checks.append('Failed optional discovery reports its own error without replacing the editor with a failed-start screen')
                context.unroute('**/api/platform/extensions/contributions',hold);context.unroute('**/api/platform/hacker',hold)
                page.wait_for_timeout(1100);page.reload();page.wait_for_function('window.lumen?.ready',timeout=15000)
                page.wait_for_function('window.lumen.activeFile==="main.py"');actual=page.evaluate('monaco.editor.getModels().find(m=>m.uri.path.endsWith("main.py")).getValue()');assert actual==expected,repr(actual)
                assert (workspace/'main.py').read_text()=='print("restored")\n';checks.append('Reload restores the unsaved buffer after optional-discovery failures without writing the source file')
                page.screenshot(path=str(args.output/'startup.png'));browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    report={'checks':checks,'errors':errors};(args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True);assert not errors


if __name__=='__main__':main()
