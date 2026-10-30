"""Actual settings/router UI; generation is an explicit fixture, not live inference."""
import json
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.ai_languages import NC_REFERENCE
from playwright.sync_api import sync_playwright,expect


def main():
    out=ROOT/'qa-output/055-ai-nc-ui';out.mkdir(exist_ok=True);checks=[];errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='zenit-ai-nc-ui-') as folder:
        folder=Path(folder);ws=folder/'project';ws.mkdir()
        source=NC_REFERENCE.split('Minimal program:\n')[1].split('\nAn entry')[0]
        (ws/'main.n').write_text(source,encoding='utf-8')
        app=Application(ROOT,ws,data_dir=folder/'profile');app.workspace.trusted=True
        app.features.studio.update({'onboarded':True})
        app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,
            'ai.provider':'emma','ai.model':'Qwen3.6-27B-Q4_K_M','ai.context':'file','security.confirmRoutineActions':False})
        def run(job,messages,system,key):
            requests.append({'provider':job.provider,'model':job.model,'messages':messages,'system':system})
            job.append('Referencia nC recibida por el transporte de prueba.');job.done=True
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with patch.object(app.features.ai,'_run',side_effect=run),sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get editor(){return editor},openFile};')
                page.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}')
                page.wait_for_function('window.lumen?.ready');page.evaluate('__qa.openFile("main.n")')
                page.wait_for_function('__qa.editor.current==="main.n"')
                page.evaluate('__qa.platform.sendAI("Explica este código",{consult:true})')
                expect(page.locator('#chat-messages')).to_contain_text('Referencia nC recibida')
                assert len(requests)==1 and requests[0]['model']=='Qwen3.6-27B-Q4_K_M'
                assert 'ref main ->> run;' in requests[0]['system'] and source in requests[0]['messages'][-1]['content']
                assert (ws/'main.n').read_text(encoding='utf-8')==source
                checks.append('Emma request retains nC source, selected model and language reference; disk unchanged')
                page.evaluate('__qa.platform.settings("ai")')
                expect(page.locator('.local-ai-model')).to_contain_text('Qwen 3.8')
                expect(page.locator('[data-local-download]')).to_contain_text('Descargar GGUF')
                assert app.features.downloads.snapshot()['items']==[]
                assert app.features.prefs.get('ai.model')=='Qwen3.6-27B-Q4_K_M'
                checks.append('Requested GGUF catalog is visible; opening settings neither downloads nor changes the model')
                for theme in ('day','dark','forest'):
                    page.evaluate('(theme)=>__qa.platform.savePreference("appearance.theme",theme)',theme)
                    card=page.locator('.local-ai-model');card.scroll_into_view_if_needed()
                    box=card.bounding_box();assert box['width']>250 and box['x']>=0 and box['x']+box['width']<=1600
                    page.screenshot(path=str(out/(theme+'.png')))
                checks.append('Model card fits the settings panel in all three built-in themes')
                # Test the real click handler without starting a 16.8GB network transfer.
                with patch.object(app.features.ai.local_models,'start',return_value={'status':'fixture-not-downloaded'}) as start:
                    page.locator('[data-local-download]').click();page.wait_for_timeout(200)
                    start.assert_called_once_with('Qwen3.8-27B-Uncensored-Q4_K_M',True)
                checks.append('Download button dispatches exact pinned model and explicit consent (download fixture)')
                # Exercise the actual activation route and preference refresh with a
                # tiny verified-file fixture. No model weights or inference are loaded.
                import hashlib
                from backend.ai_models import MODEL_CATALOG
                content=b'GGUF local activation fixture';file=app.features.downloads.root/MODEL_CATALOG[0]['file'];file.write_bytes(content)
                tiny={**MODEL_CATALOG[0],'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
                stat=file.stat()
                app.features.downloads.items['fixture']={'id':'fixture','name':tiny['file'],'url':app.features.ai.local_models.url(tiny),
                    'sha256':tiny['sha256'],'bytes':len(content),'total':len(content),'status':'complete','path':str(file),
                    'verifiedSize':stat.st_size,'verifiedMtimeNs':stat.st_mtime_ns,'error':''}
                with patch('backend.ai_models.MODEL_CATALOG',(tiny,)),patch('backend.emma.models',return_value={'models':[tiny['id']]}) as probe:
                    page.locator('[data-local-refresh]').click();expect(page.locator('[data-local-use]')).to_be_visible()
                    page.locator('[data-local-use]').click()
                    page.wait_for_function('(id)=>__qa.platform.prefs["ai.model"]===id',arg=tiny['id'])
                    assert app.features.prefs.get('ai.model')==tiny['id'];probe.assert_called_once()
                checks.append('Use in Emma activates the verified model through the real route and updates the model selector (engine discovery fixture)')
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors,'generation':'explicit fixture; no live inference'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(checks),'errors':errors},ensure_ascii=False))


if __name__=='__main__':main()
