import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {createRequire} from 'node:module';
const createAPI=createRequire(import.meta.url)(process.env.ZENIT_EXTENSION_API_PATH||'../backend/extension_api.cjs');
test('Real diagnostic collections merge batches, remain independent, iterate typed URIs and emit coalesced changes',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'zenit-diagnostics-'));const host={registerCommand:()=>({dispose(){}}),register:()=>({dispose(){}}),notify(){},effect(){},execute(){},service:async()=>({})};
 try{
  const {vscode:v}=createAPI(host,{id:'qa.diagnostics',manifest:{},root,workspace:root,storage:root,extensions:[]});const uri=v.Uri.file(path.join(root,'main.c')),range=new v.Range(0,0,0,3),a=new v.Diagnostic(range,'first'),b=new v.Diagnostic(range,'second',v.DiagnosticSeverity.Warning),c=v.languages.createDiagnosticCollection('lint'),other=v.languages.createDiagnosticCollection('lint');
  assert.equal(a.severity,0);assert.equal(v.DiagnosticTag.Deprecated,2);const events=[];const listener=v.languages.onDidChangeDiagnostics(e=>events.push(e));
  c.set([[uri,[a]],[uri,[b]]]);assert.equal(c.get(uri).length,2);assert.throws(()=>c.get(uri).push(a));assert.ok(c.has(uri));other.set(uri,[b]);
  assert.equal(v.languages.getDiagnostics(uri).length,3);const grouped=v.languages.getDiagnostics();assert.equal(grouped.length,1);assert.ok(grouped[0][0] instanceof v.Uri);assert.equal(grouped[0][1].length,3);
  let calls=0;c.forEach((u,ds,owner)=>{assert.ok(u instanceof v.Uri);assert.equal(ds.length,2);assert.equal(owner,c);calls++;});assert.equal(calls,1);assert.equal([...c].length,1);
  await Promise.resolve();assert.equal(events.length,1);assert.equal(events[0].uris.length,1);
  c.set([[uri,[a]],[uri,undefined],[uri,[b]]]);assert.deepEqual(c.get(uri),[b]);c.dispose();assert.equal(v.languages.getDiagnostics(uri).length,1);other.clear();await Promise.resolve();assert.equal(v.languages.getDiagnostics().length,0);listener.dispose();other.dispose();
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
