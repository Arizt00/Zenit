"""Real Monaco/profile transactions; AI generation uses a declared fixture transport."""
import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];requests=[]
    def passed(text):checks.append(text);print('PASS',text,flush=True)
    with tempfile.TemporaryDirectory(prefix='zenit-session-profile-') as tmp:
        base=Path(tmp);ws=base/'project';ws.mkdir()
        (ws/'main.py').write_text('print("active")\n');(ws/'keep.py').write_bytes(b'\xef\xbb\xbfprint("disk")\r\n');(ws/'asset.bin').write_bytes(b'\x00\xfffixture')
        external=base/'external.py';external.write_text('# external source\n')
        app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True
        app.features.studio.update({'onboarded':True,'displayName':'Perfil de prueba','recent':[{'path':'main.py','workspace':str(ws),'openedAt':'2026-10-13T17:29:00Z'},{'path':'keep.py','workspace':str(ws),'openedAt':'2026-10-12T17:29:00Z'}]})
        app.features.prefs.update({'security.confirmRoutineActions':False,'general.showWelcome':True,'appearance.motion':True,'updates.automatic':False,'ai.provider':'ollama','ai.model':'qa-fixture'})
        gate=threading.Event();gate.set()
        def transport(job,messages,system,hkey):
            requests.append(messages[-1]['content']);gate.wait(15)
            question=messages[-1]['content'].split('<file-inventory>')[0]
            if 'external.py' in question:ops=[{'kind':'update','path':external.as_posix(),'content':'# external changed\n'}]
            elif 'asset.bin' in question:ops=[{'kind':'delete','path':'asset.bin'}]
            elif 'borra keep.py' in question.lower():ops=[{'kind':'delete','path':'keep.py'}]
            else:ops=[{'kind':'update','path':'keep.py','content':'print("changed")\n'}]
            job.append(json.dumps({'summary':'Cambios solicitados','operations':ops}));job.done=True
        app.features.ai._run=transport
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1672,'height':917});page.on('pageerror',lambda e:errors.append(str(e)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get studio(){return studio},get editor(){return editor},get platform(){return platformUI},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready&&__qa.editor.kind==="monaco"')
                def shot(name):
                    page.evaluate('async()=>{const a=document.querySelector("#modal")?.getAnimations({subtree:true})||[];await Promise.all(a.filter(x=>x.effect?.getComputedTiming().iterations!==Infinity).map(x=>x.finished.catch(()=>{})))}')
                    page.screenshot(path=str(out/name),animations='disabled')
                expect(page.locator('.welcome-sky i')).to_have_count(18);page.screenshot(path=str(out/'welcome.png'))
                page.evaluate('document.documentElement.dataset.motion="off"');assert page.locator('.welcome-sky i').first.evaluate('(e)=>{const s=getComputedStyle(e);return s.animationPlayState==="paused"||s.animationName==="none"}')
                page.evaluate('document.documentElement.dataset.motion="on"');passed('Fullscreen sky has subtle motion and pauses with the motion preference')
                page.evaluate('__qa.studio.enter();__qa.studio.editProfile()')
                fixture=base/'portrait.png';image=Image.new('RGB',(480,320),'#654078');draw=ImageDraw.Draw(image);draw.rectangle((0,0,230,320),fill='#77c8de');draw.ellipse((200,90,400,290),fill='#f08792');image.save(fixture)
                page.locator('#profile-picture').set_input_files(str(fixture));page.wait_for_function('document.querySelector(".profile-portrait").classList.contains("has-picture")')
                def same_cover():
                    return page.evaluate('()=>{const a=document.querySelector("#profile-crop"),b=document.querySelector(".profile-portrait-cover canvas");return a.toDataURL()===b.toDataURL()}')
                assert same_cover();page.locator('#profile-zoom').fill('1.7');assert same_cover()
                crop=page.locator('#profile-crop').bounding_box();page.mouse.move(crop['x']+80,crop['y']+80);page.mouse.down();page.mouse.move(crop['x']+115,crop['y']+85);page.mouse.up();assert same_cover()
                assert 'blur(12px)' in page.locator('.profile-portrait-cover canvas').evaluate('(e)=>getComputedStyle(e).filter')
                page.locator('#profile-name').fill('Mi espacio');shot('profile-day.png');page.locator('.profile-form .primary-button').click();expect(page.locator('.profile-form')).to_have_count(0)
                avatar=app.features.studio.export()['avatar'];assert avatar.startswith('data:image/webp;base64,');passed('Profile cover uses the exact photo crop and follows zoom/drag; actual WebP persists')
                page.evaluate('__qa.studio.editProfile()');page.wait_for_function('document.querySelector(".profile-portrait").classList.contains("has-picture")');page.locator('#remove-avatar').click();assert not page.locator('.profile-portrait').evaluate('(e)=>e.classList.contains("has-picture")');page.keyboard.press('Escape');assert app.features.studio.export()['avatar']==avatar
                passed('Removing a photo clears both previews; cancel keeps the saved identity')
                for theme in ('day','dark'):
                    page.evaluate('(t)=>{document.documentElement.dataset.theme=t;__qa.studio.editProfile()}',theme);page.wait_for_function('document.querySelector(".profile-portrait").classList.contains("has-picture")');shot(f'profile-{theme}.png');page.keyboard.press('Escape')
                    page.evaluate('__qa.studio.showActivity()');shot(f'activity-{theme}.png');assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.keyboard.press('Escape')
                passed('Profile and accepted Activity layout render in light/dark without global overflow')
                for width,height in ((1366,768),(800,600),(640,360)):
                    page.set_viewport_size({'width':width,'height':height});page.evaluate('__qa.studio.editProfile()');expect(page.locator('#profile-name')).to_be_visible();assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');shot(f'profile-{width}x{height}.png');page.keyboard.press('Escape')
                page.set_viewport_size({'width':1672,'height':917});page.evaluate('__qa.studio.enter()');page.evaluate('__qa.openFile("keep.py")');page.wait_for_function('__qa.editor.current==="keep.py"');page.evaluate('__qa.editor.models.get("keep.py").model.setValue(\'print("unsaved")\\n\')');page.evaluate('__qa.openFile("main.py")');page.wait_for_function('__qa.editor.current==="main.py"')
                def ask(question,expected):
                    page.locator('#ai-input').fill(question);page.locator('#ai-form .send-button').click();expect(page.locator('.chat-message.assistant').last).to_contain_text(expected,timeout=20000);page.wait_for_function('!__qa.platform.aiJob&&!__qa.platform.aiStarting')
                ask('Modifica keep.py para imprimir changed','Aplicado 1 cambio')
                assert not page.locator('#confirm-yes').count();assert (ws/'keep.py').read_bytes()==b'\xef\xbb\xbfprint("changed")\r\n';assert __import__('re').search(r'unsaved',requests[-1]);assert 'print(\\"active\\")' not in requests[-1]
                assert page.evaluate('__qa.editor.models.get("keep.py").model.getValue()')=='print("changed")\n';page.screenshot(path=str(out/'melody-session-applied.png'));passed('Named non-active dirty file is actual model context and applies directly without a confirmation; BOM/CRLF persist')
                page.locator('.chat-message.assistant').last.get_by_role('button',name='Deshacer este plan').click();expect(page.locator('.chat-message.assistant').last).to_contain_text('Plan deshecho')
                assert (ws/'keep.py').read_bytes()==b'\xef\xbb\xbfprint("disk")\r\n';assert page.evaluate('__qa.editor.models.get("keep.py").model.getValue()')=='print("unsaved")\n';assert page.evaluate('__qa.editor.isDirty("keep.py")');passed('Undo restores both disk bytes and the earlier unsaved Monaco buffer')
                ask('Borra keep.py','Aplicado 1 cambio');assert not (ws/'keep.py').exists();assert not page.evaluate('__qa.editor.models.has("keep.py")')
                page.locator('.chat-message.assistant').last.get_by_role('button',name='Deshacer este plan').click();expect(page.locator('.chat-message.assistant').last).to_contain_text('Plan deshecho');assert page.evaluate('__qa.editor.models.get("keep.py").model.getValue()')=='print("unsaved")\n';passed('Explicit deletion closes the authorized dirty document; undo reopens its unsaved text')
                ask('Borra asset.bin','Aplicado 1 cambio');assert not (ws/'asset.bin').exists();page.locator('.chat-message.assistant').last.get_by_role('button',name='Deshacer este plan').click();expect(page.locator('.chat-message.assistant').last).to_contain_text('Plan deshecho');assert (ws/'asset.bin').read_bytes()==b'\x00\xfffixture';passed('Named binary deletion and recovery work through the actual UI')
                page.evaluate('(path)=>__qa.openFile(path)',str(external));ask('Modifica external.py','Aplicado 1 cambio');assert external.read_text()=='# external changed\n';assert page.evaluate('__qa.editor.getValue()')=='# external changed\n';page.locator('.chat-message.assistant').last.get_by_role('button',name='Deshacer este plan').click();expect(page.locator('.chat-message.assistant').last).to_contain_text('Plan deshecho');assert external.read_text()=='# external source\n';assert page.evaluate('__qa.editor.getValue()')=='# external source\n';passed('An actual external file opened in Monaco updates and undoes with Windows path aliases')
                gate.clear();page.locator('#ai-input').fill('Modifica keep.py para imprimir changed');page.locator('#ai-form .send-button').click();page.wait_for_function('!!__qa.platform.aiJob');page.evaluate('__qa.editor.models.get("keep.py").model.setValue("# newer user edit\\n")');page.wait_for_timeout(400);gate.set();expect(page.locator('.chat-message.assistant').last).to_contain_text('cambió',timeout=20000);assert (ws/'keep.py').read_bytes()==b'\xef\xbb\xbfprint("disk")\r\n';assert page.evaluate('__qa.editor.models.get("keep.py").model.getValue()')=='# newer user edit\n';passed('A user edit during generation cancels application and preserves the newer buffer')
                assert not errors,errors;passed('No uncaught JavaScript errors');browser.close()
        finally:gate.set();server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'aiTransport':'Deterministic fixture; actual AI quality is not measured.'},indent=2),encoding='utf-8')
if __name__=='__main__':main()
