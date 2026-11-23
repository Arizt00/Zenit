import test from 'node:test';
import assert from 'node:assert/strict';
import {extensionRequests} from '../web/src/extension-requests.js';

function fixture(){
 const events=new Set(),calls=[];let resolve,reject;
 const api=(path,body)=>{calls.push({path,body});return path.endsWith('/cancel')?Promise.resolve({}):new Promise((a,b)=>{resolve=a;reject=b;});};
 const model={isDisposed:()=>false,onDidChangeContent(fn){events.add(fn);return {dispose:()=>events.delete(fn)};}};
 return {group:extensionRequests(api),model,events,calls,reply:value=>resolve(value),fail:error=>reject(error)};
}
test('typing cancels the transport and returns promptly, late results cannot reappear',async()=>{
 const f=fixture(),promise=f.group.request({id:'extension'},f.model);await Promise.resolve();for(const fn of [...f.events])fn();
 const result=await promise;assert.equal(result.cancelled,true);assert.equal(f.calls[0].body.requestKey,f.calls[1].body.requestKey);assert.equal(f.events.size,0);f.reply({items:['stale']});
});
test('provider disposal cancels active queries but leaves commands outside this helper alone',async()=>{
 const f=fixture(),promise=f.group.request({id:'extension'},f.model);await Promise.resolve();f.group.dispose();assert.equal((await promise).cancelled,true);assert.equal(f.calls.length,2);assert.equal((await f.group.request({id:'extension'},f.model)).cancelled,true);
});
test('successful responses release listeners and do not send cancellation',async()=>{
 const f=fixture(),promise=f.group.request({id:'extension'},f.model);await Promise.resolve();f.reply({items:['current']});assert.deepEqual(await promise,{items:['current']});assert.equal(f.events.size,0);f.group.dispose();assert.equal(f.calls.length,1);
});
test('a Monaco cancellation token reaches the backend even without a source edit',async()=>{
 const f=fixture();let cancel;const token={onCancellationRequested(fn){cancel=fn;return {dispose(){}};}};const promise=f.group.request({id:'extension'},f.model,token);await Promise.resolve();cancel();assert.equal((await promise).cancelled,true);f.fail(Error('late transport failure'));
});
