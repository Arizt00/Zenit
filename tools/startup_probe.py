"""Repeat real WebView2 boots with a delayed bridge, in an isolated profile."""
import argparse
import json
import socket
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import webview
    from playwright.sync_api import sync_playwright
    from backend.server import Application, LumenServer
    from backend.desktop import DesktopAPI

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cycles', type=int, default=6)
    parser.add_argument('--bridge-delay', type=float, default=.8)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    import os
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={port}'
    records, errors, failure = [], [], []
    with tempfile.TemporaryDirectory(prefix='zenit-startup-') as tmp:
        workspace = Path(tmp)/'project'
        workspace.mkdir()
        (workspace/'Example.java').write_text('public class Example { int value = 42; }\n')
        app = Application(ROOT, workspace, data_dir=Path(tmp)/'profile')
        app.desktop = True
        app.features.studio.update({'onboarded': True})
        app.features.prefs.update({'updates.automatic': False, 'appearance.motion': False})
        server = LumenServer(0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        api = DesktopAPI()
        api._application, api._url = app, base
        api._window = webview.create_window('Zénit · prueba de apertura', 'about:blank', js_api=api, width=1280, height=800)
        # Delay only TEST injection, before its UMD libraries reach the document.
        original_run = api._window.run_js
        def delayed_run(script):
            if 'pywebview.domJSON = factory' in script:
                time.sleep(args.bridge_delay)
            return original_run(script)
        api._window.run_js = delayed_run

        def run():
            try:
                with sync_playwright() as pw:
                    deadline = time.monotonic()+35
                    while True:
                        try:
                            browser = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=1000)
                            break
                        except Exception:
                            if time.monotonic() > deadline:
                                raise
                    page = browser.contexts[0].pages[0]
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                    for cycle in range(args.cycles):
                        before, started = len(errors), time.monotonic()
                        page.goto(base, wait_until='domcontentloaded')
                        page.wait_for_function('window.lumen?.ready || !document.querySelector("#connection-overlay")?.classList.contains("hidden")', timeout=45000)
                        page.wait_for_function('typeof window.pywebview?.api?.status === "function"', timeout=15000)
                        amd = page.evaluate('''() => new Promise(resolve => window.require(['vs/basic-languages/java/java'],
                            module => resolve({java:!!module?.language?.tokenizer}), error => resolve({error:String(error)})))''')
                        state = page.evaluate('''() => ({ready:!!window.lumen?.ready, editor:window.lumen?.editorKind,
                            bridge:typeof window.pywebview?.api?.status, domJSON:typeof window.pywebview?.domJSON,
                            webview2:!!window.chrome?.webview, boot:window.zenitStartup?.snapshot?.(),
                            screen:document.documentElement.dataset.screen})''')
                        state.update(cycle=cycle+1, elapsedSeconds=round(time.monotonic()-started, 3), amd=amd, errors=errors[before:])
                        records.append(state)
                        print(json.dumps(state, ensure_ascii=False), flush=True)
                    page.screenshot(path=str(args.output/'startup-final.png'))
            except Exception:
                failure.append(traceback.format_exc())
            finally:
                api._window.destroy()

        try:
            webview.start(run, gui='edgechromium')
        finally:
            api._window.run_js = original_run
            app.features.shutdown()
            app.runner.shutdown()
            server.shutdown()
            server.server_close()
    result = {'method':'Real WebView2 and DesktopAPI; isolated generated Java project; background injection delayed only by this test.',
              'bridgeDelaySeconds':args.bridge_delay, 'records':records, 'failure':failure}
    (args.output/'startup.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if failure or any(not r['ready'] or r['editor'] != 'monaco' or r['domJSON'] != 'object' or not r['amd'].get('java') or r['errors'] for r in records):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
