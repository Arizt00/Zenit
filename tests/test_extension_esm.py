"""Real ESM/CJS interoperability, status/log output, and installed Prettier."""
import io,json,tempfile,time,unittest,zipfile
from pathlib import Path
from backend.server import Application
from backend.extension_runtime import Host
from backend.runtime_paths import find_tool
from backend.extensions import localized_manifest
from backend.extension_services import text_edit
ROOT=Path(__file__).resolve().parents[1]

class ESMExtensionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.ws=self.base/'project';self.ws.mkdir();(self.ws/'main.js').write_text('const x={a:1,b:2}\n')
  self.app=Application(ROOT,self.ws,data_dir=self.base/'profile');self.app.workspace.trusted=True;self.runtime=self.app.features.extension_runtime;self.host=None
 def tearDown(self):
  if self.host:self.host.close()
  self.app.features.shutdown();self.app.runner.shutdown();self.tmp.cleanup()
 def install(self,name,source,dependencies=()):
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   z.writestr('extension/package.json',json.dumps({'publisher':'qa','name':name,'version':'1.0.0','type':'module','main':'main.js','extensionDependencies':list(dependencies)}));z.writestr('extension/main.js',source)
  store=self.app.features.extensions;store.install(store.inspect_bytes(raw.getvalue())['ticket'],True)
 def call(self,command):return self.runtime.request(self.app.workspace,{'id':'qa.esm','method':'command','command':command}).get('result')
 def test_named_default_namespace_and_create_require_share_one_api(self):
  self.install('esm',"""import v,{commands,LanguageStatusSeverity} from 'vscode';import * as ns from 'vscode';import {createRequire} from 'node:module';const cjs=createRequire(import.meta.url)('vscode');export function activate(context){commands.registerCommand('qa.identity',()=>({same:v===cjs&&v===ns.default&&v.commands===commands,extension:context.extension.id,severity:LanguageStatusSeverity.Error}));}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertEqual(self.call('qa.identity'),{'same':True,'extension':'qa.esm','severity':2})
 def test_authorized_esm_dependency_uses_its_own_context_and_api(self):
  self.install('esm-dependency',"""import v from 'vscode';export function activate(context){v.commands.registerCommand('qa.dependency',()=>({id:context.extension.id,apiMatches:context.extension.extensionPath===context.extensionPath}));return {id:context.extension.id};}""")
  self.install('esm',"""import v from 'vscode';export function activate(context){v.commands.registerCommand('qa.identity',()=>({self:context.extension.id,dependency:v.extensions.getExtension('qa.esm-dependency').exports.id}));}""",['qa.esm-dependency'])
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertEqual(self.call('qa.identity'),{'self':'qa.esm','dependency':'qa.esm-dependency'});self.assertEqual(self.call('qa.dependency')['id'],'qa.esm-dependency')
 def test_unknown_esm_export_is_rejected_without_stub(self):
  self.install('esm',"import {InventedApi} from 'vscode';export function activate(){}")
  with self.assertRaisesRegex(ValueError,"does not provide an export named 'InventedApi'"):self.runtime.start(self.app.workspace,'qa.esm',True)
 def test_custom_text_editor_resolves_into_real_webview(self):
  self.install('esm',"""import v from 'vscode';export function activate(){v.window.registerCustomEditorProvider('qa.text',{resolveCustomTextEditor(doc,panel){panel.webview.html='<p>'+doc.getText()+'</p>';panel.webview.onDidReceiveMessage(async()=>{const edit=new v.WorkspaceEdit();edit.insert(doc.uri,new v.Position(0,0),'// custom editor ñ\\n');await v.workspace.applyEdit(edit);});}});v.commands.registerCommand('qa.custom',()=>v.commands.executeCommand('vscode.openWith',v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,'main.js'),'qa.text'));}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.call('qa.custom');panel=self.app.features.extension_services.snapshot()['panels'][0];self.assertIn('const x=',panel['html'])
  self.runtime.request(self.app.workspace,{'id':'qa.esm','method':'webviewMessage','panel':panel['id'],'message':{'edit':True}})
  deadline=time.monotonic()+5
  while 'main.js' not in self.app.features.buffers.items and time.monotonic()<deadline:time.sleep(.02)
  self.assertTrue(self.app.features.buffers.items['main.js']['text'].startswith('// custom editor ñ'));self.assertEqual((self.ws/'main.js').read_text(),'const x={a:1,b:2}\n')
 def test_port_attributes_are_evaluated_and_disposable(self):
  self.install('esm',"""import v from 'vscode';export function activate(){const d=v.workspace.registerPortAttributesProvider({portRange:[8000,8100],commandPattern:'python'},{providePortAttributes:value=>new v.PortAttributes(value.port===8080?v.PortAutoForwardAction.Ignore:v.PortAutoForwardAction.Notify)});v.commands.registerCommand('qa.dispose',()=>d.dispose());}""")
  self.runtime.start(self.app.workspace,'qa.esm',True)
  def ports():return self.runtime.request(self.app.workspace,{'id':'qa.esm','method':'ports','ports':[{'port':8080,'commandLine':'python app.py'},{'port':8081,'commandLine':'node app.js'}]})['items']
  self.assertEqual(ports(),[{'port':8080,'attributes':{'autoForwardAction':6}}]);self.call('qa.dispose');self.assertEqual(ports(),[])
 def test_environment_mutations_reach_a_real_terminal_and_are_workspace_scoped(self):
  self.install('esm',"""import v from 'vscode';export function activate(context){const c=context.environmentVariableCollection;c.persistent=false;c.replace('ZENIT_QA_ENV','base');c.append('ZENIT_QA_APPEND','append');c.prepend('ZENIT_QA_PREPEND','prepend');c.getScoped(v.workspace.workspaceFolders[0]).replace('ZENIT_QA_SCOPED','workspace');v.commands.registerCommand('qa.env',async()=>{const t=v.window.createTerminal({name:'QA env',shellPath:process.execPath,shellArgs:['-e','console.log(process.env.ZENIT_QA_ENV+" "+process.env.ZENIT_QA_APPEND+" "+process.env.ZENIT_QA_PREPEND+" "+process.env.ZENIT_QA_SCOPED)']});await t.processId;return t.name;});}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);time.sleep(.05);self.call('qa.env');terminal=next(iter(self.app.features.terminals.sessions.values()));deadline=time.monotonic()+8
  while not terminal.closed and time.monotonic()<deadline:time.sleep(.02)
  self.assertIn('base append prepend workspace',terminal.read()['data']);other=self.app.features.extension_services.environment(self.base/'other');self.assertNotIn('ZENIT_QA_SCOPED',other)
 def test_status_and_log_channels_reach_backend_and_dispose(self):
  self.install('esm',"""import v from 'vscode';export function activate(){const item=v.languages.createLanguageStatusItem('qa.status','javascript');item.name='QA';item.text='Listo ñ';item.detail='Resultado real';const output=v.window.createOutputChannel('QA',{log:true});v.commands.registerCommand('qa.logs',async()=>{output.debug('invisible');output.warn('aviso ñ');output.error(new Error('error real'));output.show();await new Promise(r=>setTimeout(r,60));return true;});v.commands.registerCommand('qa.dispose',async()=>{item.dispose();output.dispose();await new Promise(r=>setTimeout(r,60));});}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertTrue(self.call('qa.logs'));state=self.app.features.extension_services.snapshot()['statusItems'];self.assertEqual(state[0]['text'],'Listo ñ')
  output=next(iter(self.app.features.extension_services.outputs.values()));self.assertIn('aviso ñ',output['text']);self.assertIn('error real',output['text']);self.assertNotIn('invisible',output['text']);self.assertTrue(output['visible'])
  self.call('qa.dispose');self.assertEqual(self.app.features.extension_services.snapshot()['statusItems'],[]);self.assertEqual(self.app.features.extension_services.outputs,{})
 def test_virtual_filesystem_dispatch_and_readonly_failures(self):
  self.install('esm',"""import v from 'vscode';export function activate(){const files=new Map(),changed=new v.EventEmitter();const provider={onDidChangeFile:changed.event,stat:u=>({type:1,ctime:0,mtime:1,size:files.get(u.path)?.length||0}),readFile:u=>files.get(u.path),writeFile:(u,b)=>{files.set(u.path,b);changed.fire([{type:v.FileChangeType.Changed,uri:u}]);},readDirectory:()=>[...files].map(([name])=>[name,1]),createDirectory(){},rename:(a,b)=>{files.set(b.path,files.get(a.path));files.delete(a.path);},delete:u=>files.delete(u.path),watch:()=>new v.Disposable()};v.workspace.registerFileSystemProvider('qa-files',provider);v.workspace.registerFileSystemProvider('qa-readonly',provider,{isReadonly:true});v.commands.registerCommand('qa.files',async()=>{const u=v.Uri.parse('qa-files:/source.py'),other=u.with({path:'/renamed.py'});await v.workspace.fs.writeFile(u,new TextEncoder().encode('print("ñ")'));const doc=await v.workspace.openTextDocument(u);await v.workspace.fs.rename(u,other,{overwrite:false});const text=new TextDecoder().decode(await v.workspace.fs.readFile(other));await v.workspace.fs.delete(other,{recursive:false});let denied=false;try{await v.workspace.fs.writeFile(v.Uri.parse('qa-readonly:/file'),new Uint8Array())}catch{denied=true}return {text,doc:doc.getText(),denied,remaining:(await v.workspace.fs.readDirectory(u)).length,writable:v.workspace.fs.isWritableFileSystem('qa-files')};});}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertEqual(self.call('qa.files'),{'text':'print("ñ")','doc':'print("ñ")','denied':True,'remaining':0,'writable':True})
 def test_resource_will_event_applies_text_edits_in_the_atomic_operation(self):
  self.install('esm',"""import v from 'vscode';export function activate(){v.workspace.onWillCreateFiles(e=>{const edit=new v.WorkspaceEdit();edit.insert(v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,'main.js'),new v.Position(0,0),'// before create ñ\\n');e.waitUntil(Promise.resolve(edit));});v.commands.registerCommand('qa.create',async()=>{const edit=new v.WorkspaceEdit();edit.createFile(v.Uri.joinPath(v.workspace.workspaceFolders[0].uri,'new.js'));return v.workspace.applyEdit(edit);});}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertTrue(self.call('qa.create'));self.assertTrue((self.ws/'new.js').is_file());self.assertTrue(self.app.features.buffers.items['main.js']['text'].startswith('// before create ñ'));self.assertEqual((self.ws/'main.js').read_text(),'const x={a:1,b:2}\n')
 def test_explicit_language_tool_invocation_runs_the_registered_tool(self):
  self.install('esm',"""import v from 'vscode';export function activate(){v.lm.registerTool('qa.sum',{invoke:async opts=>new v.LanguageModelToolResult([new v.LanguageModelTextPart(String(opts.input.a+opts.input.b))])});v.commands.registerCommand('qa.tool',()=>v.lm.invokeTool('qa.sum',{input:{a:20,b:22}}));}""")
  self.runtime.start(self.app.workspace,'qa.esm',True);self.assertEqual(self.call('qa.tool'),{'content':[{'value':'42'}]})
 def prettier(self):
  roots=list((Path.home()/'AppData/Local/LumenStudio/extensions').glob('esbenp.*/extension'))
  if not roots:self.skipTest('El paquete real de Prettier no está instalado en este equipo.')
  root=roots[0];manifest=localized_manifest(root,'es');eid='esbenp.prettier-vscode';options={'extensionId':eid,'manifest':manifest,'extensions':[{'id':eid,'root':str(root),'manifest':manifest}],'dependencies':[],'storage':str(self.base/'storage'),'locale':'es'}
  self.host=Host(find_tool('node'),root,root/manifest['main'],self.app.workspace,options,self.app.features.extension_services)
 def format(self,text):
  return self.host.request({'method':'provide','kind':'format','document':{'path':'main.js','text':text,'language':'javascript','dirty':True},'options':{'tabSize':2,'insertSpaces':True}})['items']
 def test_installed_prettier_formats_real_unsaved_javascript(self):
  self.prettier();original='const x={a:1,b:2}\n';edits=self.format(original);self.assertEqual(text_edit(original,edits),'const x = { a: 1, b: 2 };\n');self.assertEqual((self.ws/'main.js').read_text(),original)
 def test_installed_prettier_respects_project_configuration(self):
  (self.ws/'.prettierrc').write_text('{"singleQuote":true,"semi":false}')
  self.prettier();original='const text="hola";\n';self.assertEqual(text_edit(original,self.format(original)),"const text = 'hola'\n")
 def test_installed_prettier_respects_ignore_file(self):
  (self.ws/'.prettierignore').write_text('main.js\n');self.prettier();self.assertEqual(self.format('const x={a:1}\n'),[])

if __name__=='__main__':unittest.main()
