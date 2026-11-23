import test from 'node:test';
import assert from 'node:assert/strict';
import {SharedExecutions} from '../web/team-execution.js';

test('two observers share one read and drain output after the process has ended',async()=>{
  let calls=0,release;
  const logs=new SharedExecutions(async body=>{calls++;if(calls===1)await new Promise(r=>release=r);return {output:body.offset?'end':'start',offset:body.offset?8:5,done:true,more:!body.offset,code:0};});
  const a=logs.read('main.py',{job:'one'}),b=logs.read('main.py',{job:'one'});release();
  const [first,second]=await Promise.all([a,b]);assert.equal(first,second);assert.equal(calls,1);assert.equal(first.done,false);
  assert.equal((await logs.read('main.py',{job:'one'})).text,'startend');assert.equal(calls,2);
  await logs.read('main.py',{job:'one'});assert.equal(calls,2);
});
test('each file has its own output and a new job resets only that file',async()=>{
  const logs=new SharedExecutions(async body=>({output:body.job,offset:3,done:true,more:false,code:0}));
  await logs.read('one.py',{job:'one'});await logs.read('two.py',{job:'two'});
  assert.equal((await logs.read('one.py',{job:'new'})).text,'new');assert.equal(logs.records.get('two.py').text,'two');
  assert.equal(await logs.read('gone.py',{job:'expired',available:false}),null);logs.clear();assert.equal(logs.records.size,0);
});
