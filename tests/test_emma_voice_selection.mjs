import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const bridge=fileURLToPath(new URL('../backend/emma_voice_bridge.mjs',import.meta.url));
function run({selected={authorized:true,defaultEngine:'qwen',id:'podcast-emma-20261004',directory:'/selected/emma'},status={personalIdentity:{active:true,id:'podcast-emma-20261004'},genericAvailable:true,mossAvailable:true},engine='qwen',speak=false}={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'zenit-voice-selection-'));fs.mkdirSync(path.join(root,'electron'));
 try{
  fs.writeFileSync(path.join(root,'electron/assistant-voices.mjs'),`export const assistantVoice=id=>{if(id!=='emma')throw Error('Wrong assistant');return ${JSON.stringify(selected)}};`);
  fs.writeFileSync(path.join(root,'electron/original-voice.mjs'),`export class OriginalVoiceRuntime{constructor(options){if(options.authorizedIdentityDirectory!==${JSON.stringify(selected.directory)})throw Error('Wrong identity path')}status(){return ${JSON.stringify(status)}}stop(){}async speak({onChunk}){onChunk({pcm:'AAAAAA==',sampleRate:24000});return {engine:${JSON.stringify(engine)}}}}`);
  const result=spawnSync(process.execPath,[bridge,root,...speak?[]:['--status']],{input:speak?'{"text":"Hola"}\n':undefined,encoding:'utf8',timeout:5000});assert.ifError(result.error);return result.stdout.trim().split('\n').map(line=>JSON.parse(line));
 }finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('The bridge selects the prepared Emma assistant voice, even when MOSS is available',()=>{
 const messages=run();assert.deepEqual(messages,[{type:'ready',engine:'qwen',identity:'podcast-emma-20261004'}]);
});
test('Missing or old identity cannot silently fall back to the older voice',()=>{
 for(const selected of [{authorized:false},{authorized:true,defaultEngine:'moss',id:'emma-moss-approved',directory:'/selected/emma'}])assert.equal(run({selected})[0].type,'error');
 const messages=run({status:{personalIdentity:{active:true,id:'podcast-emma-20261004'},genericAvailable:false,mossAvailable:true}});assert.equal(messages[0].type,'error');
});
test('The declared identity and the completed engine must match the new voice',()=>{
 assert.equal(run({status:{personalIdentity:{active:true,id:'other-voice'},genericAvailable:true}})[0].type,'error');
 const failed=run({engine:'moss',speak:true});assert.equal(failed.at(-1).type,'error');assert.ok(!failed.some(x=>x.type==='done'));
 const passed=run({speak:true});assert.deepEqual(passed.at(-1),{type:'done',engine:'qwen'});
});
