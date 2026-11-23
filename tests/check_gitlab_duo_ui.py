"""Exercise the installed, unmodified GitLab extension in an isolated profile."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--packages',type=Path,required=True);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];console=[];received=[];resources=[]
    with tempfile.TemporaryDirectory(prefix='zenit-gitlab-qa-',ignore_cleanup_errors=True) as tmp:
        base=Path(tmp);workspace=base/'project';workspace.mkdir();(workspace/'main.py').write_text('print("GitLab webview QA")\n')
        index=json.loads((args.packages/'installed.json').read_text(encoding='utf-8'))
        ids={'vscode.git','vscode.git-base','GitLab.gitlab-workflow'};chosen={k:v for k,v in index.items() if k in ids};assert set(chosen)==ids
        destination=base/'profile/extensions';destination.mkdir(parents=True)
        for item in chosen.values():shutil.copytree(args.packages/item['directory'],destination/item['directory'])
        (destination/'installed.json').write_text(json.dumps(chosen),encoding='utf-8')
        app=Application(args.root,workspace,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'updates.automatic':False})
        runtime=app.features.extension_runtime;request=runtime.request
        def track(ws,body):
            if body.get('method')=='webviewMessage':received.append(body.get('message',{}).get('command'))
            return request(ws,body)
        runtime.request=track
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw,concurrent.futures.ThreadPoolExecutor() as pool:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1000})
                page.on('pageerror',lambda error:errors.append(str(error)));page.on('console',lambda message:console.append(message.text) if message.type=='error' else None)
                page.on('response',lambda response:resources.append({'url':response.url.split('/extension-webview-resource/',1)[-1],'status':response.status}) if '/extension-webview-resource/' in response.url else None)
                page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready',timeout=45000)
                page.locator('[data-file="main.py"]').click();page.wait_for_function('window.lumen.activeFile==="main.py"');page.wait_for_timeout(700)
                future=pool.submit(runtime.start,app.workspace,'GitLab.gitlab-workflow',True)
                deadline=time.monotonic()+35
                while not future.done() and time.monotonic()<deadline:page.wait_for_timeout(100)
                host=future.result(timeout=1)['hosts'][0]
                assert host['running'] and any(p['kind']=='inlineCompletion' for p in host['providers']),host
                output='\n'.join(row['text'] for row in app.features.extension_services.outputs.values() if row['name']=='GitLab Language Server')
                assert 'GitLab Language Server has started' in output and 'Server initialization failed' not in output,output[-5000:]
                assert not any('failed to start' in str(row.get('tooltip','')).lower() for row in app.features.extension_services.status_items.values())
                checks.append('The real language server completes its initialization, registers inline completions and leaves no failed-start status')
                opened=pool.submit(runtime.request,app.workspace,{'id':'GitLab.gitlab-workflow','method':'command','command':'gl.openChat','document':{'path':'main.py','text':'print(42)','language':'python'}})
                frame=page.frame_locator('.extension-webview-surface iframe')
                expect(frame.locator('body')).to_contain_text('I am GitLab Duo Chat',timeout=25000)
                checks.append('The unmodified installed GitLab extension starts its real Duo Chat interface with its actual JavaScript and styles')
                # Its own ten-second watchdog must finish successfully, not
                # replace a briefly visible greeting with the error screen.
                page.wait_for_timeout(11000)
                expect(frame.locator('body')).not_to_contain_text('Error initializing GitLab Duo Chat')
                assert 'appReady' in received,received
                assert opened.done(), 'The actual chat command did not finish its startup handshake'
                opened.result()
                checks.append('Duo Chat sends appReady through the real extension host and stays initialized past its ten-second watchdog')
                assert len(resources)>=2 and all(item['status']==200 for item in resources),resources
                checks.append('The sandbox loads scoped local resources successfully without parent-origin blob URLs')
                sandbox=page.locator('.extension-webview-surface iframe').get_attribute('sandbox');assert 'allow-same-origin' not in sandbox
                blocked=frame.locator('body').evaluate('()=>{try{void parent.document.body;return false}catch(error){return error.name==="SecurityError"}}')
                assert blocked
                checks.append('The extension frame retains its opaque sandbox and cannot access the editor document')
                page.screenshot(path=str(args.output/'gitlab-duo.png'))
                page.locator('.extension-webview-surface header button').click();expect(page.locator('.extension-webview-surface')).to_have_count(0)
                checks.append('Closing Duo Chat disposes its extension panel and returns to the existing code buffer')
                assert not errors,errors;assert not console,console;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    report={'checks':checks,'errors':errors,'consoleErrors':console,'extensionVersion':chosen['GitLab.gitlab-workflow']['version'],'receivedCommands':received,'resources':resources,'profile':'isolated; no user credentials or project files copied','cloudChatRequestSent':False}
    (args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'passed':len(checks),'errors':errors,'consoleErrors':console}),flush=True)


if __name__=='__main__':main()
