import argparse,hashlib,json,os,re,shutil,socket,subprocess,sys,tempfile,threading,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from backend.desktop import DesktopAPI
from playwright.sync_api import sync_playwright
from PIL import Image
WORK=Path(__file__).resolve().parent
REFS=['bd406600-b2be-41dc-9ce2-b62263fe207f','8934dcf0-5cd8-4f93-83a7-83b6c616d3b5','23fac157-6c6f-478b-a308-8b68fe98c269','f497b8bd-1730-473b-b525-b8987919fd8a','2d308b7e-a03f-4033-892e-da76a8656adc','9f89f886-1900-4d71-9293-72e2ec61ba7e','866e9f6f-6af1-4b0c-b542-0d68be1fc348','6230177f-9bcf-4848-bc72-c1c4881a86d3']
NAMES=['editor','welcome','search','settings','forge','laboratory','debug','extensions']
JAVA='''package java_inicial;

public class E1 {

    public static void main(String[] args) {
        System.out.println("=== Ejercicio 1 ===");
        System.out.println("Hola, mundo desde Zénit IDE!");

        // Calcular la suma de los primeros n números
        int n = 10;
        int suma = 0;

        for (int i = 1; i <= n; i++) {
            suma += i;
        }

        System.out.println("La suma de los primeros " + n + " números es: " + suma);

        // Ejemplo de arreglo
        int[] numeros = {1, 2, 3, 4, 5};
        System.out.println("Elementos del arreglo:");
        for (int num : numeros) {
            System.out.println(" - " + num);
        }
    }
}
'''

def inventory(out):
    files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    sources=[p for p in files if p.endswith(('.js','.cjs','.mjs','.py','.css','.html','.cpp','.h','.spec','.yml'))]
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    sheets=re.findall(r'href="(/[^" ]+\.css)"',html)
    styles='\n'.join((ROOT/'web'/p.lstrip('/')).read_text(encoding='utf-8') for p in sheets)
    data={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'trackedFiles':len(files),'sourceFiles':len(sources),'stylesheets':sheets,'cssBytes':len(styles.encode()),'importantDeclarations':styles.count('!important'),'transitionAll':len(re.findall(r'transition\s*:\s*all\b',styles)),'sources':sources,'references':[]}
    refs=out/'references';refs.mkdir(parents=True,exist_ok=True)
    for name,key in zip(NAMES,REFS):
        original=ROOT/'tests/visual/references'/(name+'.png')
        copy=refs/(name+'.png');shutil.copy2(original,copy)
        with Image.open(copy) as im:dim=im.size
        data['references'].append({'screen':name,'file':str(copy),'size':dim,'sha256':hashlib.sha256(copy.read_bytes()).hexdigest()})
    (out/'audit.json').write_text(json.dumps(data,indent=2),encoding='utf-8')

def capture(page,base,out,core=False,screenshot_scale='css',profile_animation=False):
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    def inject(route):
        response=route.fetch();route.fulfill(response=response,body=response.text()+"\nwindow.__zenitQa={get editor(){return editor},get studio(){return studio},get platform(){return platformUI},get dock(){return dock},get desktop(){return desktopUI},get profiles(){return workspaceProfiles},openFile,closeFile,perform,openPalette};")
    page.route('**/src/app.js',inject);page.goto(base+'?diagnostics=1');page.wait_for_function('window.lumen?.ready',timeout=45000)
    page.evaluate('async()=>{await __zenitQa.openFile("Web.html");await __zenitQa.openFile("prueba.sm");await __zenitQa.openFile("java-inicial/E1.java");await __zenitQa.openFile("prueba.asm");await __zenitQa.openFile("java-inicial/E1.java");await __zenitQa.closeFile("Web.html");await __zenitQa.closeFile("prueba.sm");}')
    page.wait_for_function('__zenitQa.editor.getValue().includes("public")&&document.querySelector(".view-lines")');page.evaluate('__zenitQa.editor.view.focus()')
    if not core:
        # This is a real ConPTY session and a real JDK execution, not copied output.
        terminal=page.evaluate('async()=>{const p=__zenitQa.platform,profiles=await p.api("/terminals/profiles"),profile=profiles.profiles.find(x=>x.id==="powershell7")||profiles.profiles.find(x=>x.id==="powershell");if(!profile||!profiles.interactiveAvailable)return null;const t=await p.openTerminal(profile.id);await p.api("/terminals/write",{id:t.id,data:"function prompt { \'PS \' + (Split-Path (Get-Location) -Leaf) + \'> \' }; Clear-Host; java java-inicial/E1.java\\r"});return t.id;}')
        if terminal:
            page.wait_for_function('Array.from(__zenitQa.platform.terminals.values()).some(t=>t.xterm&&Array.from({length:t.xterm.buffer.active.length},(_,i)=>t.xterm.buffer.active.getLine(i)?.translateToString()||"").join("\\n").includes("La suma de los primeros 10 números es: 55"))',timeout=30000)
    page.wait_for_function('Array.from(document.querySelectorAll("canvas[data-glass]")).every(c=>c.parentElement.classList.contains("gpu-ready")||c.dataset.graphicsError)',timeout=20000)
    geometry={};inspection={}
    def snap(name):
        page.wait_for_function('Array.from(document.querySelectorAll("canvas[data-glass]")).filter(c=>c.getClientRects().length&&getComputedStyle(c).visibility!=="hidden").every(c=>c.parentElement.classList.contains("gpu-ready")||c.dataset.graphicsError)',timeout=20000)
        page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        page.screenshot(path=str(out/(name+'.png')),scale=screenshot_scale)
        geometry[name]=page.evaluate('()=>Object.fromEntries([".topbar",".activity-rail","#dock-left","#dock-right","#dock-bottom","#project-panel","#editor-panel","#assistant-panel","#terminal-panel","#platform-page","#lumen-home",".welcome-sheet",".welcome-scene",".welcome-copy",".welcome-copy h1",".assistant-hero>.glass-art",".melody-copy h3",".global-search",".editor-tabbar",".breadcrumbs"].map(s=>{let e=document.querySelector(s),r=e?.getBoundingClientRect();return [s,r?{x:r.x,y:r.y,width:r.width,height:r.height,display:getComputedStyle(e).display}:null]}))')
        geometry[name]['overflow']=page.evaluate('()=>({html:document.documentElement.scrollWidth>innerWidth,body:document.body.scrollWidth>innerWidth,topbar:document.querySelector(".topbar").scrollWidth>innerWidth,editorWidth:document.querySelector("#editor-panel").clientWidth})')
        inspection[name]=page.evaluate('()=>Object.fromEntries([".topbar",".brand-name",".global-search",".activity-rail",".tree-entry",".file-tab",".breadcrumbs",".assistant-heading",".assistant-hero>.glass-art",".melody-copy h3",".ai-action-card",".ai-composer",".terminal-toolbar",".home-sidebar",".profile-photo",".home-sidebar>h1",".home-hero",".hero-copy h2",".recent-section",".recent-file",".search-intro h2",".studio-search-field",".search-filters",".search-empty",".settings-overlay>.platform-page",".settings-layout",".settings-navigation",".settings-content",".preference-row",".extension-hero",".extension-card",".lab-heading",".lab-tools",".lab-tool",".lab-sections",".debug-intro",".lantern-workbench",".lantern-features",".lantern-question",".debug-controls",".debug-card",".forge-dashboard",".floating-panel",".forge-main",".command-palette"].map(selector=>{const e=document.querySelector(selector);if(!e||!e.getClientRects().length)return [selector,null];const r=e.getBoundingClientRect(),s=getComputedStyle(e);return [selector,{bounds:[r.x,r.y,r.width,r.height],font:[s.fontFamily,s.fontSize,s.fontWeight,s.lineHeight],padding:s.padding,gap:s.gap,radius:s.borderRadius,border:s.border,background:s.backgroundColor,color:s.color,opacity:s.opacity,blur:s.backdropFilter,shadow:s.boxShadow}];}))')
        (out/'inspection.json').write_text(json.dumps(inspection,indent=2),encoding='utf-8')
    caption=page.locator('#lantern-monitor [data-lantern-path]').text_content();assert caption=='Continuidad para tu código',repr(caption)
    pseudo=page.locator('#lantern-monitor [data-lantern-summary]').evaluate('e=>getComputedStyle(e,"::before").content');assert not re.search('[\u00c3\u00c2\ufffd]',pseudo),repr(pseudo)
    snap('editor');page.evaluate('__zenitQa.dock.show("assistant",{animate:false})');snap('melody');
    composer=page.locator('.ai-composer').bounding_box();assert composer and composer['y']+composer['height']<=page.evaluate('innerHeight'),composer
    if page.evaluate('innerWidth<1100'):page.evaluate('__zenitQa.dock.compactOpen=false;__zenitQa.dock.render()')
    if not core:
        from tools.visual_profile import measure
        performance=measure(page,2,sample_frames=False);(out/'performance.json').write_text(json.dumps(performance,indent=2),encoding='utf-8')
        stability=page.evaluate('async()=>{const q=__zenitQa,orb=document.querySelector("canvas[data-glass=orb]"),models=q.editor.models,engines=BABYLON.EngineStore.Instances.length;await q.dock.floatPanel("assistant");q.dock.reset();q.studio.home();const hero=document.querySelector("canvas[data-glass=welcome]");q.studio.enter();q.studio.home();q.studio.enter();let themes=0,old=q.editor.changedTheme;q.editor.changedTheme=()=>{themes++;old.call(q.editor);};q.platform.applyPreferences();q.editor.changedTheme=old;return {orbRetained:orb===document.querySelector("canvas[data-glass=orb]"),homeCanvasRetained:hero===document.querySelector("canvas[data-glass=welcome]"),modelsRetained:models===q.editor.models,enginesBefore:engines,enginesAfter:BABYLON.EngineStore.Instances.length,repeatedPreferencesThemeChanges:themes};}')
        assert stability['orbRetained'] and stability['homeCanvasRetained'] and stability['modelsRetained'] and not stability['repeatedPreferencesThemeChanges'],stability
        (out/'stability.json').write_text(json.dumps(stability,indent=2),encoding='utf-8')
        if profile_animation:
            page.evaluate('async()=>await __zenitQa.platform.savePreference("appearance.motion",true)');animated=measure(page,3);(out/'performance-animated.json').write_text(json.dumps(animated,indent=2),encoding='utf-8');page.evaluate('async()=>await __zenitQa.platform.savePreference("appearance.motion",false)')
    page.evaluate('__zenitQa.studio.home()');snap('welcome')
    if profile_animation and not core:
        page.evaluate('async()=>await __zenitQa.platform.savePreference("appearance.motion",true)');welcome_profile=measure(page,3);(out/'performance-welcome-animated.json').write_text(json.dumps(welcome_profile,indent=2),encoding='utf-8');page.evaluate('async()=>await __zenitQa.platform.savePreference("appearance.motion",false)')
    optical=page.evaluate('()=>{const c=document.querySelector("canvas[data-glass=welcome]"),gl=c.getContext("webgl2"),r=c.getBoundingClientRect();const e=BABYLON.EngineStore.Instances.at(-1),s=e.scenes[0];return {context:gl?.getContextAttributes(),rect:{x:r.x,y:r.y,w:r.width,h:r.height},meshes:s.meshes.map(m=>({name:m.name,alpha:m.material?.alpha,emissive:m.material?.emissiveColor?.asArray(),type:m.material?.getClassName()}))}}')
    (out/'optical.json').write_text(json.dumps(optical,indent=2),encoding='utf-8');page.evaluate('__zenitQa.studio.enter()')
    if core:
        (out/'baseline.json').write_text(json.dumps({'geometry':geometry,'errors':errors},indent=2),encoding='utf-8');return
    page.evaluate('__zenitQa.studio.search()');snap('search');page.evaluate('__zenitQa.platform.closePage()')
    page.evaluate('__zenitQa.platform.settings("general")');page.wait_for_selector('#settings-content');snap('settings')
    stats=page.evaluate('async()=>{let content=document.querySelector("#settings-content"),nav=document.querySelector(".settings-navigation"),count=0;const m=new MutationObserver(x=>count+=x.length);m.observe(document.querySelector("#platform-page"),{subtree:true,childList:true,attributes:true});await __zenitQa.platform.settings("appearance");await __zenitQa.platform.settings("general");m.disconnect();return {contentRetained:content===document.querySelector("#settings-content"),navigationRetained:nav===document.querySelector(".settings-navigation"),mutations:count}}');assert stats['contentRetained'] and stats['navigationRetained'],stats
    retained=page.evaluate('async()=>{const q=__zenitQa,shell=document.querySelector("#settings-content"),field=document.querySelector(".settings-category:not([hidden]) [data-preference]");shell.scrollTop=160;field.focus({preventScroll:true});const before=shell.scrollTop;await q.platform.settings("editor");shell.scrollTop=80;await q.platform.settings("general");return {scrollRestored:Math.abs(shell.scrollTop-before)<1,focusRestored:document.activeElement===field};}');assert all(retained.values()),retained
    stats.update(retained)
    identifiers=page.evaluate('()=>{const ids=[...document.querySelectorAll("#settings-content [id]")].map(e=>e.id);return ids.filter((id,i)=>ids.indexOf(id)!==i);}');assert not identifiers,identifiers
    page.evaluate('__zenitQa.platform.closePage()')
    page.evaluate('__zenitQa.platform.extensions()');page.wait_for_selector('.extension-hero');snap('extensions');page.evaluate('__zenitQa.platform.closePage()')
    page.locator('.foundation-toggle').click();page.wait_for_selector('.lab-tools');snap('laboratory');page.evaluate('__zenitQa.openFile("prueba.asm")');page.locator('.foundation-toggle').click();page.wait_for_selector('#lab-assembly');page.locator('#lab-assembly').click();page.locator('[data-asm=run]').click();page.wait_for_selector('.asm-status');
    assembly=page.evaluate('()=>__zenitQa.profiles.assembly.result');assert int(assembly['registers']['rax'],16)==55,assembly
    (out/'assembly.json').write_text(json.dumps(assembly,indent=2),encoding='utf-8');snap('asm');page.evaluate('__zenitQa.openFile("java-inicial/E1.java")')
    page.evaluate('__zenitQa.profiles.tools.hidden=true;__zenitQa.studio.debug()');page.wait_for_selector('#debug-state');snap('debug');page.evaluate('__zenitQa.platform.closePage()')
    page.evaluate('__zenitQa.dock.floatPanel("project")');snap('floating-project');page.evaluate('__zenitQa.dock.reset()')
    page.evaluate('__zenitQa.openPalette()');snap('palette');page.keyboard.press('Escape')
    page.evaluate('__zenitQa.dock.show("assistant",{animate:false})');page.locator('.assistant-heading-title h2').click();page.wait_for_selector('.melody-provider-details.is-open');page.keyboard.press('Escape');assert not page.locator('.melody-provider-details').is_visible()
    if page.evaluate('innerWidth<1100'):page.evaluate('__zenitQa.dock.compactOpen=false;__zenitQa.dock.render()')
    page.evaluate('__zenitQa.platform.useConsole()')
    page.evaluate('async()=>{await __zenitQa.platform.savePreference("hacker.enabled",true);__zenitQa.desktop.showForgeConsole();__zenitQa.dock.floatPanel("console",{x:339,y:91,width:980,height:668});}');snap('forge')
    page.goto(base+'?panel=forge');page.wait_for_function('window.lumen?.ready',timeout=45000);snap('forge-detached')
    (out/'baseline.json').write_text(json.dumps({'geometry':geometry,'settings':stats,'errors':errors,'realRuntime':True,'fixture':'Isolated generated source project; no simulated tool results or AI responses.'},indent=2),encoding='utf-8')
    if terminal:page.evaluate('async(id)=>{await __zenitQa.platform.api("/terminals/close",{id});}',terminal)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'build/visual');ap.add_argument('--native',action='store_true');ap.add_argument('--matrix',action='store_true');ap.add_argument('--all-views',action='store_true');ap.add_argument('--profile',action='store_true');ap.add_argument('--installed-from',type=Path);args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);inventory(out)
    with tempfile.TemporaryDirectory(prefix='zenit-visual-') as folder:
        ws=Path(folder)/'EJERCICIOSPRACTICAS';ws.mkdir()
        for sub in ['.vscode','java-inicial','lib','recursos','out']:(ws/sub).mkdir()
        (ws/'java-inicial/E1.java').write_text(JAVA,encoding='utf-8');(ws/'java-inicial/EJ2.java').write_text('class EJ2 {}',encoding='utf-8');(ws/'java-inicial/E2DinamicArrays.java').write_text('class E2DinamicArrays {}',encoding='utf-8')
        (ws/'prueba.asm').write_text((ROOT/'examples/asm/x86_64_sum.s').read_text(encoding='utf-8'),encoding='utf-8');(ws/'prueba.sm').write_text('; Unrecognized suffix remains a real plain-text file.\n',encoding='utf-8');(ws/'Web.html').write_text('<!doctype html><h1>Zénit</h1>',encoding='utf-8')
        from backend.foundation import bundled_tool,tool_environment
        if compiler:=bundled_tool('javac'):
            env=os.environ.copy();env.update(tool_environment());compiled=subprocess.run([compiler,'-encoding','UTF-8','java-inicial/E1.java','java-inicial/EJ2.java'],cwd=ws,env=env,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            if compiled.returncode:raise RuntimeError(compiled.stderr.decode('utf-8',errors='replace'))
        profile=Path(folder)/'profile'
        if args.installed_from:
            # Read-only package copies; never copy credentials or runtime approvals.
            ids={'shd101wyy.markdown-preview-enhanced','vscjava.vscode-maven','meta.pyrefly','ms-python.debugpy'};source=args.installed_from.resolve();index=json.loads((source/'installed.json').read_text(encoding='utf-8-sig'));selected={key:value for key,value in index.items() if key in ids};dest=profile/'extensions';dest.mkdir(parents=True)
            for item in selected.values():
                path=(source/item['directory']).resolve()
                if path.parent!=source or path.is_symlink():raise ValueError('Unsafe installed package path')
                shutil.copytree(path,dest/item['directory'])
            (dest/'installed.json').write_text(json.dumps(selected),encoding='utf-8')
        app=Application(ROOT,ws,data_dir=profile);app.workspace.trusted=True;app.features.studio.update({'onboarded':True,'displayName':'L4CE'});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'appearance.theme':'day','updates.automatic':False,'general.restoreLayout':False,'editor.fontSize':14})
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
        try:
            if args.native:
                import webview
                with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
                webview.settings['REMOTE_DEBUGGING_PORT']=port
                api=DesktopAPI();api._application=app;api._url=base;api._window=webview.create_window('Zénit · auditoría visual',base,js_api=api,width=1672,height=965)
                failed=[]
                def run():
                    try:
                        with sync_playwright() as pw:
                            end=time.monotonic()+40
                            while True:
                                try:browser=pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}',timeout=1000);break
                                except Exception:
                                    if time.monotonic()>end:raise
                            page=browser.contexts[0].pages[0];page.wait_for_function('window.lumen?.ready',timeout=45000)
                            w,h,scale=page.evaluate('[innerWidth,innerHeight,devicePixelRatio]');api._window.resize(round(api._window.width+(1672-w)),round(api._window.height+(917-h)))
                            # WinForms rounds physical pixels at 150% DPI. Pin the renderer
                            # viewport through CDP rather than stretching the screenshot.
                            session=browser.contexts[0].new_cdp_session(page);session.send('Emulation.setDeviceMetricsOverride',{'width':1672,'height':917,'deviceScaleFactor':scale,'mobile':False});page.wait_for_function('innerWidth===1672&&innerHeight===917')
                            (out/'native-viewport.json').write_text(json.dumps({'hostScale':scale,'rendererViewport':[1672,917],'method':'Real WebView2 + native DesktopAPI, viewport pinned through CDP; CSS-pixel capture.'}),encoding='utf-8');capture(page,base,out,profile_animation=args.profile)
                    except Exception:failed.append(traceback.format_exc())
                    finally:api._window.destroy()
                webview.start(run,gui='edgechromium')
                if failed:raise RuntimeError(failed[0])
            else:
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(channel='msedge',headless=True)
                    if args.matrix:
                        results=[]
                        for width,height in ((1280,720),(1366,768),(1440,900),(1920,1080),(2560,1440),(3840,2160)):
                            for scale in (1,1.25,1.5,2):
                                app.features.prefs.update({'hacker.enabled':False});app.features.studio.update({'workspaceStyle':'general'})
                                path=out/f'{width}x{height}-{scale}';path.mkdir(exist_ok=True);context=browser.new_context(viewport={'width':round(width/scale),'height':round(height/scale)},device_scale_factor=scale);page=context.new_page();capture(page,base,path,core=not args.all_views,screenshot_scale='device');data=json.loads((path/'baseline.json').read_text());results.append({'physical':[width,height],'scale':scale,'css':[round(width/scale),round(height/scale)],'errors':data['errors'],'overflow':{k:v['overflow'] for k,v in data['geometry'].items()}});context.close();print('Matrix',width,height,scale,flush=True)
                        (out/'matrix.json').write_text(json.dumps({'method':'Edge browser device-scale emulation; not a Windows DPI switch.','results':results},indent=2),encoding='utf-8')
                    else:
                        page=browser.new_page(viewport={'width':1672,'height':917});capture(page,base,out,profile_animation=args.profile)
                    browser.close()
        finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
    print('Captured '+str(out))
if __name__=='__main__':main()
