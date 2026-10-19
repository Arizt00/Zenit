"""Real theme packages and Monaco: readable chrome, transitions and recovery."""
import argparse,json,shutil,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.server import Application,LumenServer
from playwright.sync_api import sync_playwright

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--installed-from',type=Path,action='append',required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--audit',action='store_true');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);errors=[];states=[];checks=[]
 with tempfile.TemporaryDirectory(prefix='zenit-055-themes-') as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();(ws/'main.c').write_text('int main(void) {\n    int value = 42;\n    return value;\n}\n');(ws/'other.c').write_text('int other(void) { return 1; }\n');dest=base/'profile/extensions';dest.mkdir(parents=True);selected={}
  for source in args.installed_from:
   index=json.loads((source/'installed.json').read_text('utf-8-sig'))
   for ident,item in index.items():
    if ident in selected:continue
    folder=(source/item['directory']).resolve();assert folder.parent==source.resolve() and not folder.is_symlink();manifest=json.loads((folder/'extension/package.json').read_text('utf-8-sig'))
    if not manifest.get('contributes',{}).get('themes'):continue
    shutil.copytree(folder,dest/item['directory']);selected[ident]={**item,'enabled':True}
  assert selected; (dest/'installed.json').write_text(json.dumps(selected),'utf-8');app=Application(ROOT,ws,data_dir=base/'profile');app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'appearance.motion':False,'updates.automatic':False});server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True);context=browser.new_context(viewport={'width':1600,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    def inject(route):
     response=route.fetch();route.fulfill(response=response,body=response.text()+'\nwindow.__qa={get editor(){return editor},get platform(){return platformUI},get desktop(){return desktopUI},openFile};')
    context.route('**/src/app.js',inject);url=f'http://127.0.0.1:{server.server_port}';page.goto(url);page.wait_for_function('window.lumen?.ready');page.evaluate('async()=>{await __qa.platform.loadContributions();await __qa.openFile("main.c");await __qa.openFile("other.c");__qa.editor.activate("main.c");__qa.editor.view.executeEdits("qa",[{range:new monaco.Range(2,17,2,19),text:"43"}]);window.retainedModel=__qa.editor.view.getModel();__qa.editor.split("other.c");}');themes=page.evaluate('__qa.platform.extensionThemes.map(t=>({id:t.id,label:t.label}))')
    inspect='''async()=>{const {contrastRatio}=await import('/src/extension-theme.js'),ct=__qa.editor.view._themeService.getColorTheme(),get=k=>ct.getColor(k)?.toString().slice(0,7),css=getComputedStyle(document.documentElement),c=k=>css.getPropertyValue('--'+k).trim();return {id:document.documentElement.dataset.extensionTheme,theme:ct.themeName,model:[...__qa.editor.models.values()].some(r=>r.model===retainedModel),dirty:__qa.editor.isDirty('main.c'),background:get('editor.background'),numbers:get('editorLineNumber.foreground'),ratios:{numbers:contrastRatio(get('editorLineNumber.foreground'),get('editor.background')),text:contrastRatio(get('editor.foreground'),get('editor.background')),field:contrastRatio(c('field-text'),c('field')),header:contrastRatio(c('chrome-text'),c('header')),rail:contrastRatio(c('rail-text'),c('rail'))},panes:document.querySelectorAll('.editor-pane').length};}'''
    for theme in themes:
     page.evaluate('async id=>{const p=__qa.platform;await p.applyExtensionTheme(p.extensionThemes.findIndex(t=>t.id===id))}',theme['id']);state=page.evaluate(inspect);states.append({'label':theme['label'],**state})
     if theme['label'] in ('Vira Palenight','One Dark Pro') or 'DARK' in theme['label']:page.screenshot(path=str(args.output/(str(len(states))+'-theme.png')))
     if not args.audit:assert all(r>=4.49 for r in state['ratios'].values()),(theme,state)
     assert state['model'] and state['dirty'] and state['panes']==2 and state['id']==theme['id'],state
    checks.append(f'{len(themes)} installed theme variants retain both panes, pending text and readable surfaces')
    for native in ('day','forest','dark'):
     page.evaluate('async name=>await __qa.platform.savePreference("appearance.theme",name)',native);assert page.evaluate('document.documentElement.dataset.theme')==native;assert not page.evaluate('document.documentElement.dataset.extensionTheme');assert page.evaluate('__qa.editor.view._themeService.getColorTheme().themeName')=='lumen-theme'
    checks.append('Native themes remove extension colours and restore Monaco')
    chosen=next(t for t in themes if t['label']=='Vira Palenight');page.evaluate('async id=>await __qa.platform.savePreference("appearance.extensionTheme",id)',chosen['id']);before=page.evaluate(inspect);page.evaluate('async()=>{await __qa.platform.savePreference("editor.fontSize",16);await __qa.platform.loadContributions();}');after=page.evaluate(inspect);assert before['background']==after['background'] and before['numbers']==after['numbers'];checks.append('Font changes and contribution reload preserve the effective palette')
    child=context.new_page();child.goto(url+'?panel=project');child.wait_for_function('window.lumen?.ready');assert child.evaluate('document.documentElement.dataset.extensionTheme')==chosen['id'];page.evaluate('async()=>await __qa.platform.savePreference("appearance.theme","day")');child.wait_for_function('document.documentElement.dataset.theme==="day"&&!document.documentElement.dataset.extensionTheme');checks.append('Separated window receives the same theme and native reset')
    page.reload();page.wait_for_function('window.lumen?.ready');assert page.evaluate('document.documentElement.dataset.theme')=='day';assert not page.evaluate('document.documentElement.dataset.extensionTheme');checks.append('Saved theme survives reload without residual extension tokens');assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
 report={'checks':checks,'themes':states,'errors':errors,'lowContrast':[s for s in states if any(r<4.49 for r in s['ratios'].values())]};(args.output/'verification.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps({'checks':checks,'themes':len(states),'lowContrast':len(report['lowContrast'])}),flush=True)
if __name__=='__main__':main()
