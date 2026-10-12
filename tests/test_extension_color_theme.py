"""Real Node extension receives current ColorThemeKind and theme change events."""
import io,json,tempfile,time,unittest,zipfile
from pathlib import Path
from backend.server import Application
ROOT=Path(__file__).resolve().parents[1]
PLUGIN="""'use strict';const v=require('vscode');let events=[];exports.activate=()=>{v.window.onDidChangeActiveColorTheme(theme=>events.push({kind:theme.kind,current:v.window.activeColorTheme.kind,same:theme===v.window.activeColorTheme}));v.commands.registerCommand('qa.theme',()=>({kind:v.window.activeColorTheme.kind,enum:v.ColorThemeKind,events}));};"""

class ColorThemeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name);ws=base/'project';ws.mkdir();self.app=Application(ROOT,ws,data_dir=base/'profile');self.app.workspace.trusted=True
  self.addCleanup(self.app.runner.shutdown);self.addCleanup(self.app.features.shutdown);store=self.app.features.extensions;raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'theme','version':'1','main':'main.cjs','contributes':{'themes':[{'id':'hc','label':'High Contrast','uiTheme':'hc-black','path':'theme.json'},{'id':'hc-light','label':'HC Light','uiTheme':'hc-light','path':'theme.json'},{'id':'other-dark','label':'Other Dark','uiTheme':'vs-dark','path':'theme.json'}]}}));z.writestr('extension/main.cjs',PLUGIN);z.writestr('extension/theme.json','{"colors":{}}')
  store.install(store.inspect_bytes(raw.getvalue())['ticket'],True);self.app.features.post('/settings',{'settings':{'appearance.theme':'dark'}});self.app.features.extension_runtime.start(self.app.workspace,'qa.theme',True)
 def state(self):return self.app.features.extension_runtime.request(self.app.workspace,{'id':'qa.theme','method':'command','command':'qa.theme'})['result']
 def wait(self,count):
  end=time.monotonic()+5
  while time.monotonic()<end:
   state=self.state()
   if len(state['events'])==count:return state
   time.sleep(.02)
  self.fail('Actual colour theme event not received')
 def test_current_theme_is_real_before_activation_and_all_four_kinds_dispatch(self):
  state=self.state();self.assertEqual(state['kind'],2);self.assertEqual(state['enum'],{'Light':1,'Dark':2,'HighContrast':3,'HighContrastLight':4});self.assertEqual(state['events'],[])
  for count,ident,kind in [(1,'qa.theme:hc',3),(2,'qa.theme:hc-light',4),(3,'qa.theme:other-dark',2),(4,'',2)]:
   self.app.features.post('/settings',{'settings':{'appearance.extensionTheme':ident}});state=self.wait(count);self.assertEqual(state['kind'],kind);self.assertEqual(state['events'][-1],{'kind':kind,'current':kind,'same':True})
  self.app.features.post('/settings',{'settings':{'appearance.theme':'day'}});self.assertEqual(self.wait(5)['kind'],1)
 def test_editor_changes_and_reapplying_same_theme_do_not_emit_spurious_colour_changes(self):
  for settings in [{'editor.fontSize':16},{'appearance.theme':'dark'},{'terminal.fontSize':14}]:self.app.features.post('/settings',{'settings':settings})
  self.assertEqual(self.state()['events'],[]);events=self.app.features.command_events;self.assertTrue(any(e['command']=='zenit.preferences.changed' for e in events))
 def test_disabling_or_invalid_theme_contributions_reports_the_actual_native_fallback(self):
  self.app.features.post('/settings',{'settings':{'appearance.extensionTheme':'qa.theme:hc'}});self.assertEqual(self.wait(1)['kind'],3)
  self.app.features.post('/settings',{'settings':{'extensions.loadContributions':False}});self.assertEqual(self.wait(2)['kind'],2)
  self.app.features.post('/settings',{'settings':{'extensions.loadContributions':True}});self.assertEqual(self.wait(3)['kind'],3)
  store=self.app.features.extensions;root=store.root/store.installed['qa.theme']['directory']/'extension';(root/'theme.json').write_text('invalid')
  self.app.features.extension_services.theme_changed();self.assertEqual(self.wait(4)['kind'],2)
