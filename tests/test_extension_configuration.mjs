import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {createRequire} from 'node:module';
const createAPI=createRequire(import.meta.url)('../backend/extension_api.cjs');
test('Configuration groups expose nested defaults, leaf overrides and current values after update',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'zenit-config-'));
 try{
  const host={registerCommand:()=>({dispose(){}}),register:()=>({dispose(){}}),notify(){},effect(){},execute(){},service:async()=>({})};
  const {vscode:v}=createAPI(host,{id:'qa.config',manifest:{contributes:{configuration:{properties:{'sample.blame.format':{default:'author'},'sample.blame.enabled':{default:true}}}}},root,workspace:root,storage:root,extensions:[]});
  const c=v.workspace.getConfiguration('sample');assert.deepEqual({...c.get('blame')},{format:'author',enabled:true});assert.equal(c.blame.format,'author');assert.equal(c.has('blame'),true);assert.equal(v.workspace.getConfiguration().sample.blame.enabled,true);
  await c.update('blame.enabled',false);assert.equal(c.get('blame.enabled'),false);assert.equal(c.get('blame').enabled,false);assert.equal(v.workspace.getConfiguration('sample.blame').get('format'),'author');assert.equal(c.inspect('blame.enabled').globalValue,false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
