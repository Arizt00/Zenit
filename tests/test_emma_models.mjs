// Explicit engine fixture: validates protocol/model/context, not inference quality.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const bridge=fileURLToPath(new URL('../backend/emma_bridge.mjs',import.meta.url));
function run({model='main-model',catalogOnly=false,external=false,content='nC language reference',maxTokens=512}={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'zenit-emma-models-'));
 try{
  fs.mkdirSync(path.join(root,'electron'));fs.mkdirSync(path.join(root,'resources/inference'),{recursive:true});
  fs.writeFileSync(path.join(root,'electron/inference-models.mjs'),`export const MAIN_MODEL={id:'main-model'};export function validateModelFile(file){return file;}`);
  fs.writeFileSync(path.join(root,'electron/model-catalog.json'),JSON.stringify([{id:'second-model'}]));
  fs.writeFileSync(path.join(root,'electron/inference-runtime.mjs'),`export class NativeInferenceRuntime {
   model(settings){if(!['main-model','second-model'].includes(settings.localModel))throw Error('Unknown');return {id:settings.localModel};}
   status(settings){try{return {available:true,model:this.model(settings).id};}catch{return {available:false};}}
   async complete(request){const resolved=this.model(request.settings);request.onDelta(JSON.stringify({model:resolved.id,context:request.settings.localContextTokens,system:request.messages[0].content}));return {metrics:{fixture:true}};}
   stop(){}
  }`);
  const spec={id:'external-model',path:path.join(root,'external.gguf'),bytes:4,sha256:'a'.repeat(64)};
  const args=[bridge,root,...catalogOnly?['--models']:['--model',model],'--model-specs',JSON.stringify(external?[spec]:[])];
  const result=spawnSync(process.execPath,args,{input:JSON.stringify({messages:[{role:'system',content}],maxTokens})+'\n',encoding:'utf8',timeout:5000});
  assert.ifError(result.error);return result.stdout.trim().split('\n').filter(Boolean).map(line=>JSON.parse(line));
 }finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('catalog lists each available Emma model without generating',()=>assert.deepEqual(run({catalogOnly:true})[0].models,['main-model','second-model']));
test('selected model reaches the engine; system reference is preserved',()=>{
 const events=run({model:'second-model'}),delta=JSON.parse(events.find(event=>event.type==='delta').text);
 assert.equal(delta.model,'second-model');assert.equal(delta.system,'nC language reference');assert.ok(delta.context>=8192);
});
test('unknown model fails explicitly instead of falling back',()=>{
 const events=run({model:'missing'});assert.equal(events[0].type,'error');assert.match(events[0].message,/no se sustituirá/);assert.equal(events.some(event=>event.type==='delta'),false);
});
test('verified Zénit addition is selected independently of Emma catalog',()=>{
 const events=run({model:'external-model',external:true});assert.equal(JSON.parse(events.find(event=>event.type==='delta').text).model,'external-model');
});
test('oversized local context fails before inference',()=>{
 const events=run({content:'x'.repeat(64000),maxTokens:4096});assert.ok(events.some(event=>event.type==='error'&&event.message.includes('32768')));assert.equal(events.some(event=>event.type==='delta'),false);
});
