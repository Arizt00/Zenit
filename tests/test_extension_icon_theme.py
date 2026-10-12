import io,json,tempfile,time,unittest,zipfile
from pathlib import Path
from backend.server import Application
from backend.extensions import icon_theme,image_data
ROOT=Path(__file__).resolve().parents[1]
SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M2 2h20v20H2Z"/></svg>'
PLUGIN="""const v=require('vscode');let events=[],colours=0;exports.activate=()=>{v.workspace.onDidChangeConfiguration(e=>events.push({icons:e.affectsConfiguration('workbench.iconTheme'),colours:e.affectsConfiguration('workbench.colorTheme')}));v.window.onDidChangeActiveColorTheme(()=>colours++);v.commands.registerCommand('qa.icons',async(change,value,target)=>{const c=v.workspace.getConfiguration('workbench');if(change)await c.update('iconTheme',value,target);return {value:c.get('iconTheme'),property:c.iconTheme,inspect:c.inspect('iconTheme'),events,colours};});};"""
class IconThemeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name);ws=base/'project';ws.mkdir();self.app=Application(ROOT,ws,data_dir=base/'profile');self.addCleanup(self.app.features.shutdown);self.addCleanup(self.app.runner.shutdown);self.app.features.trust(True);raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':'icons','version':'1','main':'main.cjs','contributes':{'iconThemes':[{'id':'qa-icons','path':'icons.json'}]}}));z.writestr('extension/main.cjs',PLUGIN);z.writestr('extension/icon.svg',SVG);z.writestr('extension/icons.json',json.dumps({'iconDefinitions':{'normal':{'iconPath':'icon.svg'},'bad':{'iconPath':'../escape.svg'},'script':{'iconPath':'bad.svg'},'glyph':{'fontCharacter':'\\E001'}},'file':'normal','folder':'normal','folderExpanded':'normal','rootFolder':'normal','folderNames':{'SRC':'normal'},'languageIds':{'python':'normal'},'light':{'folder':'normal'},'hidesExplorerArrows':True,'fonts':[{'id':'glyphs','src':[{'path':'icons.woff'}]}]}));z.writestr('extension/icons.woff',b'wOFF'+b'\0'*40);z.writestr('extension/bad.svg','<svg><script>alert(1)</script></svg>')
  store=self.app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True)
 def test_declarations_load_folders_variants_languages_and_bounded_local_fonts(self):
  self.assertTrue(image_data(b'<svg><defs><path id="shape" d="M0 0h2"/></defs><use href="#shape"/></svg>',allow_local_use=True).startswith('data:image/svg+xml;'))
  for raw in [b'<svg><use href="https://example.com/a"/></svg>',b'<svg><use href="data:text/html,test"/></svg>',b'<svg><use href="file:///private.svg"/></svg>']:
   with self.assertRaises(ValueError):image_data(raw,allow_local_use=True)
  theme=self.app.features.extensions.contributions()['iconThemes'][0];self.assertEqual(theme['folderNames'],{'src':'normal'});self.assertEqual(theme['light']['folder'],'normal');self.assertEqual(theme['languageIds']['python'],'normal');self.assertEqual(theme['configurationId'],'qa-icons');self.assertTrue(theme['hidesExplorerArrows']);self.assertEqual(theme['rejectedResources'],2);self.assertEqual(theme['definitions']['glyph']['fontCharacter'],'\ue001');self.assertEqual(len(theme['fonts']),1);self.assertNotIn('bad',theme['definitions']);self.assertNotIn('script',theme['definitions'])
 def state(self,*args):return self.app.features.extension_runtime.request(self.app.workspace,{'id':'qa.icons','method':'command','command':'qa.icons','arguments':list(args)})['result']
 def test_real_node_configuration_persists_selection_null_reset_and_events(self):
  self.app.features.extension_runtime.start(self.app.workspace,'qa.icons',True);self.assertEqual(self.state()['value'],'qa-icons');self.state(True,None);self.assertEqual(self.app.features.prefs.get('appearance.iconTheme'),'none');end=time.monotonic()+5
  while time.monotonic()<end and not self.state()['events']:time.sleep(.02)
  state=self.state();self.assertIsNone(state['value']);self.assertIsNone(state['property']);self.assertEqual(state['events'][0],{'icons':True,'colours':False});self.assertEqual(state['colours'],0);self.state(True,'qa-icons');self.assertEqual(self.app.features.prefs.get('appearance.iconTheme'),'qa.icons:qa-icons')
  with self.assertRaises(ValueError):self.state(True,'missing')
  with self.assertRaises(ValueError):self.state(True,'qa-icons',2)
  self.app.features.post('/settings',{'settings':{'appearance.iconTheme':'zenit'}});self.assertEqual(self.app.features.extension_services.icon_state()['configurationId'],'zenit')
