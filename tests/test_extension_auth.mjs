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

test('Built-in GitHub account is empty before connection and requires each extension grant',async()=>{
 const storage=mkdtempSync(join(tmpdir(),'zenit-auth-builtin-'));let sessions=[],consents=0;
 const host={registerCommand:()=>({dispose(){}}),register:()=>({dispose(){}}),notify(){},effect(){},execute(){},service:async(method,p)=>{assert.equal(p.provider,'github');if(method==='authentication.sessions')return sessions;if(method==='authentication.create')throw Error('Connect in Settings');throw Error(method);}};
 const bridge=createAPI(host,{id:'qa.github-consumer',manifest:{},root:storage,workspace:storage,storage,extensions:[],authenticationProviders:['github']}),api=bridge.vscode;
 api.window.showQuickPick=async items=>{consents++;return items[0];};
 try{
  assert.equal(await api.authentication.getSession('github',['repo'],{silent:true}),undefined);
  await assert.rejects(api.authentication.getSession('github',['repo'],{createIfNone:true}),/Settings/);
  sessions=[{id:'github-fixture-session',accessToken:'fixture-only',account:{id:'42',label:'QA'},scopes:['repo']}];
  assert.equal(await api.authentication.getSession('github',['repo'],{silent:true}),undefined);
  assert.equal((await api.authentication.getSession('github',['repo'],{createIfNone:true})).account.id,'42');
  assert.equal((await api.authentication.getSession('github',['repo'],{silent:true})).id,'github-fixture-session');
  bridge.services.event('authentication.changed',{provider:'github'});
  assert.equal(await api.authentication.getSession('github',['repo'],{silent:true}),undefined);assert.equal(consents,2);
 }finally{rmSync(storage,{recursive:true,force:true});}
});
