"""Actual installed theme declarations and computed foreground/background pairs."""
import argparse,json,shutil,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--installed-from',type=Path,required=True);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='zenit-r7-theme-') as tmp:
        base=Path(tmp);ws=base/'Aurora';ws.mkdir();(ws/'main.py').write_text('count=41\nprint(count+1)\n');profile=base/'profile';dest=profile/'extensions';dest.mkdir(parents=True)
        source=args.installed_from.resolve();index=json.loads((source/'installed.json').read_text('utf-8-sig'));selected={}
        for key,item in index.items():
            directory=(source/item['directory']).resolve();assert directory.parent==source and not directory.is_symlink()
            manifest=json.loads((directory/'extension/package.json').read_text('utf-8-sig'))
            if manifest.get('contributes',{}).get('themes'):
                shutil.copytree(directory,dest/item['directory']);selected[key]=item
        (dest/'installed.json').write_text(json.dumps(selected));app=Application(ROOT,ws,data_dir=profile);app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'en','general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'extensions.checkUpdatesOnOpen':False})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917})
                def inject(route):
                    response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get platform(){return platformUI},get editor(){return editor},openFile};')
                context.route('**/src/app.js',inject);page=context.new_page();page.on('pageerror',lambda e:errors.append(e.stack));page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('async()=>{await __qa.openFile("main.py");window.__model=__qa.editor.view.getModel();await __qa.platform.extensions();}')
                themes=page.evaluate('__qa.platform.extensionThemes.map(t=>({id:t.id,label:t.label}))');assert len(themes)>=64
                for theme in themes:
                    page.evaluate('(id)=>__qa.platform.applyExtensionTheme(__qa.platform.extensionThemes.findIndex(t=>t.id===id))',theme['id'])
                    state=page.evaluate('''async()=>{const {contrastRatio}=await import('/src/extension-theme.js');const s=getComputedStyle(document.documentElement),get=k=>s.getPropertyValue('--'+k).trim(),pairs=[['text','surface'],['secondary','surface'],['muted','surface'],['field-text','field'],['button-text','button-end'],['chrome-text','header'],['selected-text','selected']];const hex=v=>{const values=v.match(/[\\d.]+/g);return '#'+values.slice(0,3).map(x=>(+x).toString(16).padStart(2,'0')).join('');};const card=document.querySelector('.extension-card'),fg=getComputedStyle(card.querySelector('h4')).color,bg=getComputedStyle(card).backgroundColor;return {ratios:Object.fromEntries(pairs.map(([a,b])=>[a,contrastRatio(get(a),get(b))])),actualCardContrast:contrastRatio(hex(fg),hex(bg)),border:contrastRatio(get('border'),get('surface')),overflow:document.documentElement.scrollWidth>innerWidth||document.getElementById('extension-results').scrollWidth>document.getElementById('extension-results').clientWidth+1,modelSame:__model===__qa.editor.view.getModel()};}''')
                    assert all(x>=4.5 for x in state['ratios'].values()),(theme,state);assert state['actualCardContrast']>=4.5 and state['border']>=1.29 and not state['overflow'] and state['modelSame'],(theme,state)
                    checks.append({'theme':theme,**state})
                    if theme['label'] in ('Bearded Theme Vivid Light','Bearded Theme Solarized Light','One Dark Pro'):page.screenshot(path=str(out/(theme['label'].lower().replace(' ','-')+'.png')),animations='disabled')
                page.evaluate('()=>__qa.platform.savePreference("appearance.extensionTheme","")');page.evaluate('()=>__qa.platform.savePreference("appearance.theme","day")');page.screenshot(path=str(out/'extensions-day.png'),animations='disabled')
                page.set_viewport_size({'width':1366,'height':768});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(out/'extensions-compact.png'),animations='disabled');assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    (out/'verification.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n');print(f'PASS {len(checks)} actual installed theme variants: computed text/field/button/card contrast, visible borders, no overflow, preserved model',flush=True)
if __name__=='__main__':main()
