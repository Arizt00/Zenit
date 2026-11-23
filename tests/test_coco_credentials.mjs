import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import crypto from 'node:crypto';

const require=createRequire(new URL('../integrations/team-vscode/extension.cjs',import.meta.url));
const source=readFileSync(new URL('../integrations/team-vscode/extension.cjs',import.meta.url),'utf8');
function fixture(){
  const exported={},secrets=new Map(),state=new Map();
  vm.runInNewContext(source,{exports:exported,require:name=>name==='vscode'?{window:{createOutputChannel:()=>({})}}:require(name),Buffer,URL,setTimeout,clearTimeout,setInterval,clearInterval});
  const context={secrets:{get:async k=>secrets.get(k),store:async(k,v)=>secrets.set(k,v)},workspaceState:{get:(k,fallback)=>state.has(k)?state.get(k):fallback,update:async(k,v)=>state.set(k,v)}};
  return {Client:exported.Client,context,secrets,state};
}

test('native VS Code credentials and pending intents follow the room across endpoint changes',async()=>{
  const f=fixture(),token='a'.repeat(43),invite='http://127.0.0.1:4000/#'+token;
  const first=new f.Client(invite,'Ana');await first.restoreCredentials(f.context,invite);
  const identity={peer:first.peer,resumeKey:first.resumeKey};await f.context.secrets.store(first.credentialKey,JSON.stringify(identity));
  f.state.set(first.credentialKey+':intents',{'document-1':'must-not-run-twice'});
  const nextInvite='https://new-endpoint.example/#'+token,next=new f.Client(nextInvite,'Ana');await next.restoreCredentials(f.context,nextInvite);
  assert.equal(next.peer,identity.peer);assert.equal(next.resumeKey,identity.resumeKey);assert.equal(next.credentialKey,first.credentialKey);
  assert.equal(f.context.workspaceState.get(next.credentialKey+':intents')['document-1'],'must-not-run-twice');
  const other=new f.Client('https://new-endpoint.example/#'+'b'.repeat(43),'Ana');await other.restoreCredentials(f.context,'https://new-endpoint.example/#'+'b'.repeat(43));
  assert.notEqual(other.peer,identity.peer);assert.notEqual(other.credentialKey,first.credentialKey);
});

test('0.2.1 identities and unacknowledged intents migrate without losing the old credential',async()=>{
  const f=fixture(),invite='http://127.0.0.1:4000/#'+'c'.repeat(43),legacy='coco:'+crypto.createHash('sha256').update(invite).digest('hex');
  f.secrets.set(legacy,JSON.stringify({peer:'legacy-peer',resumeKey:'d'.repeat(43)}));f.state.set(legacy+':intents',{'document-2':'lost-response'});
  const client=new f.Client(invite,'Bea');await client.restoreCredentials(f.context,invite);
  assert.equal(client.peer,'legacy-peer');assert.equal(f.context.workspaceState.get(client.credentialKey+':intents')['document-2'],'lost-response');assert.ok(f.secrets.has(legacy));
});
