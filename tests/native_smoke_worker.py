"""Run with the packaged zenit-python helper, using its embedded modules/runtime."""
import argparse
import concurrent.futures
from contextlib import contextmanager
import io
import hashlib
import json
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from urllib.request import urlopen
from pathlib import Path
import webview
from backend.server import Application, LumenServer
from backend.desktop import DesktopAPI
from backend.version import PRODUCT_NAME, REVISION


def until(fn,timeout=60):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            result=fn()
            if result:return result
        except Exception:pass
        time.sleep(.15)
    raise AssertionError('Packaged native operation timed out')


@contextmanager
def native_workspace():
    temporary=tempfile.TemporaryDirectory(prefix='lumen-native-package-')
    target=Path(temporary.name).resolve()
    assert target.parent==Path(tempfile.gettempdir()).resolve() and target.name.startswith('lumen-native-package-')
    try:yield temporary.name
    finally:
        # WebView2/ConPTY release native handles just after window shutdown.
        # Retry only this verified test directory; never hide a cleanup failure.
        for attempt in range(20):
            try:temporary.cleanup();break
            except PermissionError:
                if attempt==19:raise
                time.sleep(.25)


def focus_native(window):
    if sys.platform.startswith('linux'):
        # Xvfb has no window manager to focus newly opened windows. Give the
        # actual X window focus; do not bypass document.hasFocus() in the app.
        import ctypes
        from webview.platforms.qt import BrowserView
        x11=ctypes.CDLL('libX11.so.6');x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
        x11.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
        x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
        display=x11.XOpenDisplay(None)
        if not display:raise AssertionError('Xvfb display unavailable')
        try:x11.XSetInputFocus(display,int(BrowserView.instances[window.uid].winId()),2,0);x11.XFlush(display)
        finally:x11.XCloseDisplay(display)
    window.evaluate_js('monaco.editor.getEditors().find(e=>e.getModel()).focus()')
    until(lambda:window.evaluate_js('document.hasFocus()'))


def main():
    javascript_errors=[]
    if sys.platform.startswith('linux'):
        from webview.platforms.qt import BrowserView
        original_console=BrowserView.WebPage.javaScriptConsoleMessage
        def console(page,level,message,line,source):
            if 'Error' in str(level):javascript_errors.append({'source':source,'line':line,'message':message})
            original_console(page,level,message,line,source)
        BrowserView.WebPage.javaScriptConsoleMessage=console
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]));checks=[];errors=[]
    source=Path(__file__).resolve().parents[1]
    for file in (source/'backend').glob('extension_*.cjs'):
        embedded=root/'backend'/file.name
        assert embedded.is_file() and embedded.read_bytes()==file.read_bytes(),file.name
    info=json.loads((root/'web/assets/zenit-crystal.mesh.json').read_text())
    mesh=(root/'web/assets/zenit-crystal.mesh.bin').read_bytes()
    assert len(mesh)==info['byteLength'] and hashlib.sha256(mesh).hexdigest()==info['sha256']
    from backend.projects import create_project
    checks.append('Frozen package includes every extension API module, verified Blender geometry and project creation')
    with native_workspace() as temp:
        base=Path(temp);workspace=base/'project';workspace.mkdir();file=workspace/'first.py';file.write_text('print("DISK")\n',encoding='utf-8')
        html='<!doctype html><html><body><h1>DISK</h1></body></html>'
        (workspace/'Web.html').write_text(html,encoding='utf-8')
        (workspace/'data.csv').write_text('name,value\none,2\n',encoding='utf-8')
        (workspace/'native.tm').write_text('ZENIT_TOKEN = 42\n/* comentario\ncontinúa */\n',encoding='utf-8')
        app=Application(root,workspace,data_dir=base/'profile');app.workspace.trusted=True
        from backend.coco_tunnel import InternetTunnel,VERSION as tunnel_version
        assert tunnel_version=='2026.10.1' and (root/'licenses/cloudflared/LICENSE').is_file()
        assert InternetTunnel(app.features,'http://127.0.0.1:1/').status()['phase']=='preparing'
        from backend.educational_asm import RARS_EXAMPLE,MARS_EXAMPLE
        for engine,architecture,code in [('rars','riscv32',RARS_EXAMPLE),('mars','mips',MARS_EXAMPLE)]:
            simulated=app.features.simulation.run(app.workspace,{'engine':engine,'architecture':architecture,'source':code,'steps':10000})
            assert simulated['status']=='complete' and '7 + 5 = 12' in simulated['output'],simulated
        app.features.studio.update({'onboarded':True});app.features.prefs.update({'general.showWelcome':False,'updates.automatic':False,'appearance.motion':False})
        grammar_vsix=io.BytesIO()
        with zipfile.ZipFile(grammar_vsix,'w') as z:
            z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'native-grammar','version':'1.0.0','license':'MIT','contributes':{'languages':[{'id':'qa-native','extensions':['.tm']}],'grammars':[{'language':'qa-native','scopeName':'source.qa-native','path':'grammar.json'}]}}))
            z.writestr('extension/grammar.json',json.dumps({'scopeName':'source.qa-native','patterns':[{'name':'keyword.control.native','match':'ZENIT_TOKEN'},{'name':'comment.block.native','begin':'/\\*','end':'\\*/'}]}))
        app.features.extensions.install(app.features.extensions.inspect_bytes(grammar_vsix.getvalue())['ticket'],True)
        # Exercise the frozen Rust CRDT extension and the shipped peer resources.
        team=app.features.team;shared=team.start(app.workspace,{'documents':[{'path':'first.py'}],'allowRun':True})
        from pycrdt import Doc,Text
        from backend.team import decode
        doc=Doc({'text':Text()});doc.apply_update(decode(team.request({'peer':'native','vectors':{}})['updates']['first.py']))
        assert str(doc['text'])=='print("DISK")\n'
        with urlopen(shared['invitation'].split('#')[0],timeout=5) as response:assert b'Z' in response.read()
        first=team.request({'action':'run','path':'first.py','requestId':'native-shared-run'})
        until(lambda:app.runner.jobs[first['job']].done)
        assert team.request({'action':'run','path':'first.py','requestId':'native-shared-run'})['job']==first['job']
        assert len(team.room.jobs)==1
        team.stop();checks.append('Frozen pycrdt converges shared buffers, serves multi-IDE clients and reuses a shared run after a lost acknowledgement')
        for target in ('vscode','jetbrains'):
            package=team.connector(target);assert hashlib.sha256(decode(package['data'])).hexdigest()==package['sha256']
        checks.append('Frozen distribution includes verified VSIX and JetBrains connector archives')
        binary=workspace/'native-binary.exe';binary.write_bytes(b'\0placeholder')
        (workspace/'native-binary.c').write_text('#include <stdio.h>\nint main(){puts("NATIVE_BINARY_R15");return 0;}\n',encoding='utf-8')
        from backend.binary_view import revision as binary_revision
        result=app.features.binary_tools.build({'path':binary.name,'source':'native-binary.c','revision':binary_revision(binary)})
        until(lambda:app.runner.jobs[result['job']].done)
        assert app.runner.jobs[result['job']].code==0,app.runner.jobs[result['job']].output
        app.features.binary_tools.finish(result);raw=binary.read_bytes();offset=raw.index(b'NATIVE_BINARY_R15')
        import base64
        result=app.features.binary_tools.save({'path':binary.name,'revision':binary_revision(binary),'patches':[{'offset':offset,'before':base64.b64encode(b'NATIVE_BINARY_R15').decode(),'after':base64.b64encode(b'PATCHED_BINARY_15').decode()}]})
        assert Path(result['backup']).is_file();checks.append('Frozen binary tools compile real C and atomically patch bytes with an original backup')
        result=app.features.hacker.start(app.workspace,binary.name,'','binary');terminal=app.features.terminals.get(result['terminal']['id'])
        until(lambda:terminal.closed);assert 'PATCHED_BINARY_15' in terminal.read()['data'];checks.append('Frozen runtime executes the edited binary in its own actual PTY')
        server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
        url=f'http://127.0.0.1:{server.server_port}';api=DesktopAPI();api._application=app;api._url=url
        # Qt exits when its last visible child closes if the parent stays hidden.
        # Linux QA runs in its own Xvfb display, so keep its parent visible there.
        api._window=webview.create_window(PRODUCT_NAME+' native package verification',url,js_api=api,width=1300,height=850,hidden=sys.platform!='linux')
        def verify():
            try:
                until(lambda:api._window.evaluate_js('!!window.lumen?.ready'))
                assert api.status()['revision']==REVISION
                assert api._window.evaluate_js('window.lumen.editorKind')=='monaco'
                title=api._window.evaluate_js('document.title')
                assert title.endswith(PRODUCT_NAME),(title,PRODUCT_NAME)
                assert api._window.evaluate_js('document.querySelector(".brand-tagline").textContent').endswith('R'+str(REVISION))
                checks.append('Packaged runtime, Monaco and native JS bridge')
                api._window.evaluate_js('document.querySelector(".coco-button").click()')
                until(lambda:api._window.evaluate_js('document.querySelectorAll(".team-network-modes>label").length===3'))
                assert api._window.evaluate_js('document.querySelectorAll(".team-entry-tabs [role=tab]").length')==2
                assert api._window.evaluate_js('document.querySelector(".team-network-modes .team-mode-copy strong").textContent')=='Este equipo'
                api._window.evaluate_js('document.querySelector("#modal [data-action=close-modal]").click()')
                until(lambda:api._window.evaluate_js('document.querySelector("#modal-backdrop").classList.contains("hidden")'))
                assert app.native.lib is not None,app.native.name
                checks.append('Native C/C++ core loaded')
                # WebView2 suspends painting in hidden windows. Token DOM checks
                # must observe a real visible editor, then restore the QA state.
                if sys.platform=='win32':api._window.show()
                api._window.evaluate_js("document.querySelector('[data-file=\"native.tm\"]').click()")
                until(lambda:api._window.evaluate_js("[...document.querySelectorAll('.view-line span span')].some(x=>x.textContent==='ZENIT_TOKEN')"))
                assert api._window.evaluate_js("(()=>{let span=[...document.querySelectorAll('.view-line span span')].find(x=>x.textContent==='ZENIT_TOKEN');const sample=document.createElement('span');sample.style.color='var(--syntax-keyword)';document.body.append(sample);const match=getComputedStyle(span).color===getComputedStyle(sample).color;sample.remove();return match;})()")
                checks.append('Packaged Oniguruma WASM and contributed TextMate grammar colour actual Monaco tokens')
                until(lambda:api._window.evaluate_js("[...document.querySelectorAll('.view-line span span')].some(x=>x.textContent.includes('continúa')&&x.classList.contains('mtki'))"))
                checks.append('Packaged TextMate tokenizer preserves multiline comments in the native webview')
                if sys.platform=='win32':api._window.hide()
                app.features.buffers.update(app.workspace,{'path':'first.py','text':'print("ZENIT NATIVE R2 ñ",flush=True)\n','sequence':0})
                api.detach_panel('forge','first.py');forge=api._children['forge']
                until(lambda:forge.evaluate_js('!!window.lumen?.ready'))
                assert forge.evaluate_js('document.documentElement.dataset.detachedPanel')=='forge'
                forge.evaluate_js("window.__qaErrors=[];window.addEventListener('error',e=>__qaErrors.push(e.message))")
                until(lambda:forge.evaluate_js('!document.querySelector("[data-action=hacker-python]").disabled'))
                forge.evaluate_js('document.querySelector("[data-action=hacker-python]").click()')
                until(lambda:any('ZENIT NATIVE R2 ñ' in session.read(0)['data'] for session in app.features.terminals.sessions.values()))
                until(lambda:forge.evaluate_js("!!document.querySelector('.xterm-screen')"))
                assert not forge.evaluate_js('window.__qaErrors')
                assert file.read_text(encoding='utf-8')=='print("DISK")\n'
                checks.append('Separate Forge window executes unsaved UTF-8 Python in real PTY')
                forge.evaluate_js('document.querySelector("[data-action=forge-terminal]").click()')
                until(lambda:'forge' not in api._children)
                checks.append('Forge returns to '+PRODUCT_NAME+' without replacing the source file')
                parent=api._window
                parent.evaluate_js("document.querySelector('[data-file=\"Web.html\"]').click()")
                until(lambda:parent.evaluate_js("window.lumen.activeFile==='Web.html'"))
                parent.evaluate_js("const select=document.querySelector('#workspace-style');select.value='web';select.dispatchEvent(new Event('change'))")
                until(lambda:parent.evaluate_js("document.documentElement.dataset.workspaceStyle==='web'"))
                parent.evaluate_js("document.querySelector('[data-profile-action=preview]').click()")
                until(lambda:parent.evaluate_js("!!document.querySelector('.workspace-profile-tools iframe')"))
                parent.evaluate_js("document.querySelector('[data-surface-panel=preview]').click()")
                preview=until(lambda:api._children.get('preview'))
                try:until(lambda:preview.evaluate_js('!!window.lumen?.ready'))
                except Exception:
                    preview.evaluate_js("window.__bootImportDiagnostic={pending:true};import('/src/app.js?boot-diagnostic').then(()=>window.__bootImportDiagnostic={evaluated:true}).catch(e=>window.__bootImportDiagnostic={error:String(e),stack:e.stack});")
                    until(lambda:preview.evaluate_js('!window.__bootImportDiagnostic.pending'),timeout=10)
                    print('IMPORT ERROR:',json.dumps(preview.evaluate_js('window.__bootImportDiagnostic'),ensure_ascii=True),flush=True)
                    details=preview.evaluate_js("JSON.stringify({url:location.href,text:document.body.innerText.slice(-2400),boot:document.documentElement.dataset.booting,readyState:document.readyState,require:typeof window.require,overlay:document.querySelector('#connection-overlay').className,resources:performance.getEntriesByType('resource').map(r=>({url:r.name,type:r.initiatorType,ms:r.duration})),scripts:[...document.scripts].map(s=>s.src)})")
                    print('PREVIEW BOOT:',json.dumps(details,ensure_ascii=True),flush=True)
                    raise
                assert preview.evaluate_js("document.querySelector('.native-auxiliary-surface').getBoundingClientRect().height>100")
                parent.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('Web.html')).setValue('<!doctype html><h1>NATIVE LIVE</h1>')")
                def rendered(window,selector,marker):
                    source=window.evaluate_js(f"document.querySelector({json.dumps(selector)})?.src")
                    return source and marker in urlopen(source,timeout=3).read().decode('utf-8')
                until(lambda:rendered(preview,'.workspace-profile-tools iframe','NATIVE LIVE'))
                assert (workspace/'Web.html').read_text(encoding='utf-8')==html
                checks.append('Native web preview receives unsaved HTML in its separate desktop window')
                preview.evaluate_js("document.querySelector('[data-surface-panel=preview]').click()")
                until(lambda:'preview' not in api._children)
                until(lambda:parent.evaluate_js("!document.querySelector('.workspace-profile-tools').hidden"))
                checks.append('Same preview control reattaches the live surface to the main native window')
                parent.evaluate_js("document.querySelector('[data-lantern=start]').click()")
                until(lambda:app.features.lantern.snapshot().get('preview'))
                parent.evaluate_js("document.querySelector('#lantern-inline [data-lantern=detach]').click()")
                lantern=until(lambda:api._children.get('lantern'))
                until(lambda:lantern.evaluate_js('!!window.lumen?.ready'))
                revision=app.features.lantern.snapshot()['revision'];time.sleep(1)
                assert app.features.lantern.snapshot()['revision']==revision
                checks.append('Native Lantern shares the active session without a duplicate execution')
                parent.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('Web.html')).setValue('<!doctype html><h1>LANTERN LIVE</h1>')")
                until(lambda:rendered(lantern,'.lantern-preview iframe','LANTERN LIVE'))
                lantern.evaluate_js("document.querySelector('[data-lantern=detach]').click()")
                until(lambda:'lantern' not in api._children)
                until(lambda:parent.evaluate_js("!document.querySelector('#lantern-inline').hidden"))
                assert (workspace/'Web.html').read_text(encoding='utf-8')==html
                checks.append('Native Lantern updates in vivo and returns without saving the source')
                parent.evaluate_js("document.querySelector('[data-lantern=stop]').click();document.querySelector('[data-file=\"data.csv\"]').click()")
                until(lambda:parent.evaluate_js("window.lumen.activeFile==='data.csv'"))
                parent.evaluate_js("const select=document.querySelector('#workspace-style');select.value='data';select.dispatchEvent(new Event('change'))")
                until(lambda:parent.evaluate_js("document.documentElement.dataset.workspaceStyle==='data'"))
                parent.evaluate_js("document.querySelector('.profile-detach').click()")
                data=until(lambda:api._children.get('profile-data'))
                until(lambda:data.evaluate_js('!!window.lumen?.ready'))
                focus_native(data)
                assert data.evaluate_js("document.querySelector('.profile-table-filter').getBoundingClientRect().width>50")
                data.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('data.csv')).setValue('name,value\\none,8\\n')")
                until(lambda:parent.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('data.csv')).getValue().includes('one,8')"))
                # Require the new adapter from the frozen package and use its actual UI.
                raw=io.BytesIO()
                with zipfile.ZipFile(raw,'w') as z:
                    z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'native-input','version':'1.0.0','main':'main.cjs'}))
                    z.writestr('extension/main.cjs',"const v=require('vscode');exports.activate=()=>{v.commands.registerCommand('qa.nativeViews',()=>v.window.visibleTextEditors.map(e=>({path:e.document.uri.fsPath,ranges:e.visibleRanges.length})));return v.commands.registerCommand('qa.nativeInput',()=>v.window.showInputBox({title:'Entrada nativa',validateInput:value=>value.length<3?'Tres letras':undefined}));};")
                store=app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True)
                runtime=app.features.extension_runtime;runtime.start(app.workspace,'qa.native-input',True)
                until(lambda:any(x['ranges']>0 and x['path'].endswith('data.csv') for x in runtime.request(app.workspace,{'id':'qa.native-input','method':'command','command':'qa.nativeViews'})['result']))
                checks.append('Packaged Monaco sends actual visible editor ranges to the Node extension')
                data.evaluate_js("document.querySelector('.profile-detach').click()")
                until(lambda:'profile-data' not in api._children)
                assert (workspace/'data.csv').read_text(encoding='utf-8')=='name,value\none,2\n'
                checks.append('Native development mode shares edits and reattaches with the same control')
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result=pool.submit(runtime.request,app.workspace,{'id':'qa.native-input','method':'command','command':'qa.nativeInput'})
                    until(lambda:parent.evaluate_js("document.querySelector('#zenit-quick-title')?.textContent==='Entrada nativa'"))
                    parent.evaluate_js("const input=document.querySelector('.zenit-quick-field input');input.value='proyecto ñ';input.dispatchEvent(new Event('input',{bubbles:true}))")
                    until(lambda:parent.evaluate_js("document.querySelector('.zenit-quick-validation')?.textContent===''"))
                    parent.evaluate_js("document.querySelector('.zenit-quick-accept').click()")
                    assert result.result(20)['result']=='proyecto ñ'
                until(lambda:parent.evaluate_js("!document.querySelector('.zenit-quickinput')"))
                checks.append('Packaged QuickInput receives native UI text and returns it to the real extension')
                def dependency_package(name,dependencies=()):
                    raw=io.BytesIO()
                    with zipfile.ZipFile(raw,'w') as z:
                        z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':name,'version':'1.0.0','license':'MIT','main':'main.cjs','extensionDependencies':list(dependencies)}))
                        z.writestr('extension/main.cjs',"exports.activate=c=>({sum:(a,b)=>a+b,id:c.extension.id});" if name=='native-child' else "const v=require('vscode');exports.activate=async()=>{const child=await v.extensions.getExtension('qa.native-child').activate();v.commands.registerCommand('qa.nativeSum',()=>({sum:child.sum(7,5),owner:child.id}));};")
                    return raw.getvalue()
                original=store.inspect_remote
                try:
                    store.inspect_remote=lambda eid,**kw:store.inspect_bytes(dependency_package('native-child'),'Open VSX')
                    root_review=store.inspect_bytes(dependency_package('native-plan',['qa.native-child']))
                    plan=store.prepare_plan(root_review['ticket']);assert len(plan['packages'])==2
                    store.install_plan(plan['plan'],True)
                    assert {'qa.native-child','qa.native-plan'}<=set(type(store)(store.prefs).installed)
                    runtime.start(app.workspace,'qa.native-plan',True)
                    assert runtime.request(app.workspace,{'id':'qa.native-plan','method':'command','command':'qa.nativeSum'})['result']=={'sum':12,'owner':'qa.native-child'}
                finally:store.inspect_remote=original
                checks.append('Packaged dependency plan persists packages and shares real function exports with their parent')
                parent.evaluate_js("document.querySelector('[data-file=\"first.py\"]').click()")
                until(lambda:parent.evaluate_js("document.querySelector('[data-tab=\"first.py\"]')?.classList.contains('active')"))
                parent.evaluate_js("window.dispatchEvent(new CustomEvent('lumen:detach-editor',{detail:{panel:'editor',path:'first.py'}}))")
                external=until(lambda:api._children.get('editor:first.py'))
                until(lambda:external.evaluate_js('!!window.lumen?.ready'))
                until(lambda:parent.evaluate_js("!document.querySelector('[data-tab=\"first.py\"]')"))
                assert external.evaluate_js("document.querySelector('.native-window-heading small').textContent")=='Búfer compartido'
                external.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('first.py')).setValue('print(\"NATIVE OWNERSHIP\")\\n')")
                assert api.focus_panel('editor','first.py')['focused'] and api._children.get('editor:first.py') is external
                external.evaluate_js("document.querySelector('.native-return').click()")
                until(lambda:'editor:first.py' not in api._children)
                until(lambda:parent.evaluate_js("document.querySelector('[data-tab=\"first.py\"]')?.classList.contains('active')"))
                assert parent.evaluate_js("monaco.editor.getModels().find(m=>m.uri.path.endsWith('first.py')).getValue()")=='print("NATIVE OWNERSHIP")\n'
                checks.append('Native detached editor transfers document visibility, focuses safely and restores its latest unsaved buffer')
                assert not javascript_errors,javascript_errors
                print(json.dumps({'checks':checks,'errors':errors}),flush=True)
            except Exception:errors.append(traceback.format_exc());print(errors[-1],flush=True)
            finally:
                for window in list(webview.windows):
                    try:window.destroy()
                    except Exception:pass
        try:webview.start(verify,gui='qt' if sys.platform.startswith('linux') else 'edgechromium' if sys.platform=='win32' else 'cocoa',private_mode=True,storage_path=str(base/'webview'))
        finally:
            server.shutdown();server.server_close();app.features.shutdown();app.runner.shutdown()
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps({'platform':sys.platform,'revision':REVISION,'checks':checks,'errors':errors,'javascriptErrors':javascript_errors},indent=2),encoding='utf-8')
    if errors or len(checks)!=20:raise AssertionError('Packaged desktop verification failed')

if __name__=='__main__':main()
