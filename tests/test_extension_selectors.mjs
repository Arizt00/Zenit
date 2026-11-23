import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {createRequire} from 'node:module';
const createAPI=createRequire(import.meta.url)('../backend/extension_api.cjs');
test('Real providers respect scheme, language and relative globs, including virtual documents and folder boundaries',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'zenit-selectors-')),handlers=[];
 const host={registerCommand:()=>({dispose(){}}),register:(kind,lang,fn)=>{handlers.push(fn);return {dispose(){}};},notify(){},effect(){},execute(){},service:async()=>({})};
 const bridge=createAPI(host,{id:'qa.selectors',manifest:{},root,workspace:root,storage:root,extensions:[]}),v=bridge.vscode;
 try{
  const uri=v.Uri.file(path.join(root,'src','main.py')),doc={uri,languageId:'python',fileName:uri.fsPath};
  assert.equal(v.languages.match('*',doc),5);assert.equal(v.languages.match({language:'python',scheme:'file',pattern:'**/*.py'},doc),10);assert.equal(v.languages.match({language:'python',scheme:'untitled'},doc),0);
  assert.equal(v.languages.match({pattern:new v.RelativePattern(path.join(root,'src'),'*.py')},doc),10);assert.equal(v.languages.match({pattern:new v.RelativePattern(path.join(root,'src-other'),'*.py')},doc),0);assert.equal(v.languages.match([],doc),0);
  assert.equal(v.workspace.getWorkspaceFolder(v.Uri.file(path.join(root,'..named','file.py')))?.index,0);assert.equal(v.workspace.getWorkspaceFolder(v.Uri.file(root+'-other/file.py')),undefined);
  assert.equal(v.workspace.asRelativePath(uri,true),path.basename(root)+'/src/main.py');assert.equal(v.workspace.getWorkspaceFolder(v.Uri.parse('untitled:/file.py')),undefined);
  let calls=0;v.languages.registerHoverProvider({language:'python',scheme:'file',pattern:'**/test_*.py'},{provideHover(){calls++;return new v.Hover('Only tests');}});
  bridge.syncDocument({path:'src/main.py',language:'python',text:'print(1)'});assert.equal(await handlers[0]({position:{line:0,character:0}}),undefined);assert.equal(calls,0);
  bridge.syncDocument({path:'src/test_main.py',language:'python',text:'print(1)'});assert.ok(await handlers[0]({position:{line:0,character:0}}));assert.equal(calls,1);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
