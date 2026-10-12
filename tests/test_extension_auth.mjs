import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const require=createRequire(import.meta.url),createAPI=require('../backend/extension_api.cjs');
test('Registered auth providers require access consent and never fabricate a missing provider',async()=>{
 const storage=mkdtempSync(join(tmpdir(),'zenit-auth-')),events=[];let accept=true;
 const api=createAPI({registerCommand:()=>({dispose(){}}),register:()=>({dispose(){}}),notify(){},effect(){},execute(){},service:async(method,p)=>{if(method==='window.pick')return accept?0:1;return {ok:true};}},{id:'qa.consumer',manifest:{},root:storage,workspace:storage,storage,extensions:[]}).vscode;
 api.window.showQuickPick=async items=>items[accept?0:1];
 const emitter=new api.EventEmitter(),sessions=[{id:'session-1',accessToken:'test-fixture-token',account:{id:'account-1',label:'QA account'},scopes:['read']}];
 const changed=api.authentication.onDidChangeSessions(e=>events.push(e)),d=api.authentication.registerAuthenticationProvider('qa-provider','QA',{onDidChangeSessions:emitter.event,getSessions:async()=>sessions,createSession:async()=>sessions[0]});
 try{
  await assert.rejects(api.authentication.getSession('missing',['read'],{silent:true}),/no conectado/);
  assert.equal(await api.authentication.getSession('qa-provider',['read'],{silent:true}),undefined);
  const session=await api.authentication.getSession('qa-provider',['read'],{createIfNone:true});assert.equal(session.id,'session-1');
  assert.equal((await api.authentication.getSession('qa-provider',['read'],{silent:true})).id,'session-1');
  emitter.fire({added:[],removed:[sessions[0]],changed:[]});assert.equal(await api.authentication.getSession('qa-provider',['read'],{silent:true}),undefined);assert.deepEqual(events[0],{provider:{id:'qa-provider',label:'QA'}});
  accept=false;await assert.rejects(api.authentication.getSession('qa-provider',['read'],{createIfNone:true}),/cancelado/);
 }finally{d.dispose();changed.dispose();rmSync(storage,{recursive:true,force:true});}
});
