"""Actual native close must persist the final keystroke before renderer teardown."""
import argparse,json,sys,tempfile,threading,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import webview
from backend.server import Application,LumenServer
from backend.desktop import DesktopAPI
from backend.version import REVISION

def until(fn,timeout=45):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   result=fn()
   if result:return result
  except Exception:pass
  time.sleep(.1)
 raise AssertionError('Native R17 operation timed out')

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);args=p.parse_args();checks=[];errors=[];root=Path(getattr(sys,'_MEIPASS',ROOT))
 with tempfile.TemporaryDirectory(prefix='zenit-native-r16-',ignore_cleanup_errors=True) as tmp:
  base=Path(tmp);ws=base/'project';ws.mkdir();file=ws/'main.py';file.write_text('print("on disk")\n');profile=base/'profile';app=Application(root,ws,data_dir=profile);app.workspace.trusted=True;app.startup={'path':'main.py'};app.features.studio.update({'onboarded':True,'workspaceStyle':'general'});app.features.prefs.update({'general.locale':'es','general.showWelcome':False,'updates.automatic':False,'security.confirmRoutineActions':False,'files.autoSave':False})
  server=LumenServer(0,app);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}';api=DesktopAPI();api._application=app;api._url=url;window=webview.create_window('R17 native session verification',url,js_api=api,width=1300,height=850,hidden=True);api._window=window;api._bind_session_close()
  final='print("last keystroke survives close")\n'
  def verify():
   try:
    until(lambda:window.evaluate_js('!!window.lumen?.ready'));assert api.status()['revision']==17;assert window.evaluate_js('window.lumen.editorKind')=='monaco';assert window.evaluate_js('!!window.zenitSessionSnapshot');checks.append('Native R17 loads the actual workbench, Monaco and session close bridge')
    window.evaluate_js('monaco.editor.getModels().find(m=>m.uri.path.endsWith("main.py")).setValue('+json.dumps(final)+');monaco.editor.getEditors().find(e=>e.getModel()).setPosition({lineNumber:1,column:12})')
    window.destroy()
   except Exception:errors.append(traceback.format_exc());window.destroy()
  try:
   webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(base/'webview'))
   state=app.features.workbenches.snapshot(app.workspace);assert not errors,errors;assert state['session']['documents'][0]['content']==final,state;assert file.read_text()=='print("on disk")\n';checks.append('Closing immediately after editing persists dirty text and cursor without saving the source')
   app.features.shutdown();assert not app.features.hilo.lifecycle_errors,list(app.features.hilo.lifecycle_errors);checks.append('HILO closes every registered subsystem without lifecycle errors')
   # A fresh backend has a new port and no in-memory cache.
   reopened=Application(root,ws,data_dir=profile);reopened.workspace.trusted=True
   try:assert reopened.features.workbenches.snapshot(reopened.workspace)['session']['documents'][0]['content']==final;checks.append('A fresh backend recovers the durable session independently of the HTTP port')
   finally:reopened.features.shutdown()
  except Exception:errors.append(traceback.format_exc())
  finally:server.shutdown();server.server_close();app.features.shutdown()
 args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps({'revision':REVISION,'frozen':bool(getattr(sys,'frozen',False)),'checks':checks,'errors':errors},indent=2),encoding='utf-8')
 if errors:raise AssertionError(errors)
 print('PASS',len(checks),'native R17 checks',flush=True)
if __name__=='__main__':main()
