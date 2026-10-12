"""Real Monaco split/settings/reload regression using the installed Bearded theme."""
import argparse,json,shutil,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--installed-from',type=Path,required=True);parser.add_argument('--audit',action='store_true');args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);states=[];errors=[]
 with tempfile.TemporaryDirectory(prefix='zenit-theme-stability-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();source='\u0023 consejo de prueba\ndef calculate(value):\n    return value + 42\n\nprint("hola")\n';(ws/'main.py').write_text(source);(ws/'other.py').write_text(source.replace('42','43'))
  origin=args.installed_from.resolve();index=json.loads((origin/'installed.json').read_text(encoding='utf-8-sig'));ident='BeardedBear.beardedtheme';info=index[ident];package=(origin/info['directory']).resolve();assert package.parent==origin and not package.is_symlink();dest=base/'profile/extensions';dest.mkdir(parents=True);shutil.copytree(package,dest/info['directory']);(dest/'installed.json').write_text(json.dumps({ident:info}))
  app=Application(ROOT,ws,data_dir=base/'profile');app.workspace.trusted=True;app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'appearance.motion':False,'updates.automatic':False,'extensions.checkUpdatesOnOpen':False});server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1672,'height':917});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},get studio(){return studio},openFile};')
    context.route('**/src/app.js',inject);page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_function('window.lumen?.ready');page.evaluate('async()=>{await __qa.openFile("main.py");await __qa.openFile("other.py");__qa.editor.activate("main.py");await __qa.platform.applyExtensionTheme(__qa.platform.extensionThemes.findIndex(t=>t.label==="Bearded Theme Solarized Light"));window.__model=__qa.editor.view.getModel();}')
    def record(name):
     if not args.audit:page.wait_for_function('[...document.querySelectorAll(".editor-pane")].every(p=>[...p.querySelectorAll(".view-line span")].some(e=>e.textContent.trim().startsWith("#")&&getComputedStyle(e).color==="rgb(176, 187, 180)"))')
     page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
     state=page.evaluate('()=>({theme:__qa.editor.view._themeService.getColorTheme().themeName,base:__qa.editor.view._themeService.getColorTheme().base,selected:document.documentElement.dataset.extensionTheme,modelRetained:[...__qa.editor.models.values()].some(r=>r.model===__model),panes:__qa.editor.panes.length,colors:[...document.querySelectorAll(".editor-pane .view-line span")].filter(e=>e.textContent.trim()).map(e=>({text:e.textContent.trim(),color:getComputedStyle(e).color})).slice(0,40)})');states.append({'step':name,**state});print(name,state['theme'],flush=True);page.screenshot(path=str(out/(name+'.png')))
    record('selected');page.evaluate('__qa.editor.split("other.py")');record('split');page.evaluate('async()=>await __qa.platform.savePreference("editor.fontSize",16)');record('font');page.evaluate('async()=>await __qa.platform.loadContributions()');record('contributions');page.evaluate('async()=>await __qa.platform.savePreference("editor.wordWrap",true)');record('wrap');page.reload();page.wait_for_function('window.lumen?.ready');page.evaluate('async()=>{await __qa.openFile("main.py");window.__model=__qa.editor.view.getModel()}');record('reload')
    if not args.audit:
     profiles=page.evaluate('__qa.platform.api("/terminals/profiles")');cmd=next(p for p in profiles['profiles'] if p['id']=='cmd');page.evaluate('async profile=>{const result=await __qa.platform.openTerminal(profile);window.__terminal=__qa.platform.terminals.get(result.id);__terminal.xterm.write("\\x1b[34mMuestra ANSI\\x1b[0m\\r\\n")}',cmd['id']);assert page.evaluate('__terminal.xterm.options.theme.blue')=='#4db0f7';assert page.evaluate('__terminal.xterm.options.theme.brightBlue')=='#45b1ff';page.evaluate('async()=>await __qa.platform.savePreference("terminal.fontSize",15)');assert page.evaluate('__terminal.xterm.options.theme.blue')=='#4db0f7';print('Terminal retains both original ANSI blues',flush=True)
    result={'states':states,'errors':errors,'passed':not errors and all(s['theme']=='lumen-extension-theme' and s['modelRetained'] for s in states),'ansiTested':not args.audit,'package':'Read-only Bearded Theme; disposable profile.'};(out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');browser.close()
    if not args.audit:assert result['passed'],result
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
if __name__=='__main__':main()
