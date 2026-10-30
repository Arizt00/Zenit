"""Opt-in visual HTTPS station test using disposable fixture code only."""
import argparse,json,shutil,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.coco_tunnel import VERSION
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--connector',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);errors=[];checks=[]
    with tempfile.TemporaryDirectory(prefix='zenit-internet-ui-',ignore_cleanup_errors=True) as temporary:
        base=Path(temporary);ws=base/'station';ws.mkdir();(ws/'shared.py').write_text('from pathlib import Path\np=Path("starts.txt")\np.write_text((p.read_text() if p.exists() else "")+"START\\n")\nprint("COCO_HTTPS_UI")\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'Estación anfitriona'});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'appearance.motion':True,'updates.automatic':False})
        connector=app.features.prefs.directory/'tools/coco'/VERSION/'cloudflared-windows-amd64.exe';connector.parent.mkdir(parents=True);shutil.copy2(args.connector,connector)
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get team(){return teamUI},get editor(){return editor},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("shared.py")');page.wait_for_function('__qa.editor.current==="shared.py"');page.evaluate('__qa.team.open()')
                page.locator('[data-team-mode][value=internet]').check();expect(page.locator('[data-team-internet-info]')).to_be_visible();boxes=page.locator('.team-network-modes>label').evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right}})');assert len(boxes)==3 and max(b['y'] for b in boxes)-min(b['y'] for b in boxes)<1;assert all(boxes[i+1]['x']-boxes[i]['right']>=10 for i in range(2));page.screenshot(path=str(out/'internet-mode.png'));page.locator('[data-team-run]').check();page.locator('[data-team-host]').click()
                expect(page.locator('[data-team-copy]')).to_be_disabled();expect(page.locator('.team-connection')).to_contain_text('Preparando');page.screenshot(path=str(out/'internet-preparing.png'))
                page.wait_for_function('__qa.team.state.invitation?.startsWith("https://")',timeout=100000);expect(page.locator('[data-team-copy]')).to_be_enabled();expect(page.locator('.team-connection')).to_contain_text('HTTPS');room=page.evaluate('__qa.team.room');invite=page.evaluate('__qa.team.state.invitation');page.screenshot(path=str(out/'internet-ready.png'));checks.append('Internet mode shows provider disclosure, asynchronous preparation and an enabled invitation only after public HTTPS is ready')
                peer=context.new_page();peer.on('pageerror',lambda e:errors.append(str(e)));peer.goto(invite);peer.locator('#name').fill('Estación invitada');peer.locator('#connect').click();peer.wait_for_function('document.querySelector("#connect").disabled');expect(peer.locator('#run')).to_be_disabled()
                member=next(m for m in app.features.team.room.project.members.values() if m['role']!='host');app.features.team.request({'action':'permissions','participant':member['id'],'role':'runner'});expect(peer.locator('#run')).to_be_enabled();peer.evaluate('monaco.editor.getModels()[0].applyEdits([{range:new monaco.Range(1,1,1,1),text:"# Internet UI 🙂\\n"}])');page.wait_for_function('__qa.editor.getValue().includes("Internet UI")');assert page.evaluate('__qa.team.room')==room;peer.locator('#save').click();expect(peer.locator('#status')).to_contain_text('Guardado');assert 'Internet UI' in (ws/'shared.py').read_text(encoding='utf-8')
                lost=[]
                def lose_run(route):
                    if route.request.post_data_json.get('action')=='run' and len(lost)<2:
                        response=route.fetch(max_retries=0);lost.append(response.status);route.abort('connectionreset')
                    else:route.continue_()
                peer.route('**/v1',lose_run);peer.locator('#run').click();expect(peer.locator('#status')).to_contain_text('fetch',timeout=25000);peer.unroute('**/v1',lose_run);assert len(lost)==2
                peer.reload();peer.locator('#connect').click();expect(peer.locator('#run')).to_be_enabled();peer.locator('#run').click();expect(peer.locator('#output')).to_contain_text('COCO_HTTPS_UI',timeout=25000);assert (ws/'starts.txt').read_text()=='START\n';assert len(app.runner.jobs)==1;peer.screenshot(path=str(out/'internet-peer.png'));checks.append('Public HTTPS preserves one participant, permissions, project text and a single host process after two dropped run acknowledgements and a guest reload')
                page.evaluate('__qa.team.open()');page.locator('[data-team-origin]').click();expect(page.locator('.team-evidence')).to_contain_text('Órdenes en el anfitrión');expect(page.locator('.team-evidence')).to_contain_text('Coincide');page.screenshot(path=str(out/'internet-execution-origin.png'));checks.append('Host opens source fingerprint, commands and current-revision validity for that same shared execution')
                page.evaluate('__qa.team.stop()');context.close();browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'scope':'Both clients use this computer; guest traffic crosses the public HTTPS endpoint.'},indent=2),encoding='utf-8');assert not errors,errors
    for check in checks:print('PASS',check,flush=True)

if __name__=='__main__':main()
