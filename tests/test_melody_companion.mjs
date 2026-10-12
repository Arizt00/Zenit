import test from 'node:test';
import assert from 'node:assert/strict';
import {CompanionSession} from '../web/src/melody-companion.js';
import {requestsRealtimeHelp} from '../web/src/ai-intent.js';

test('Direct real-time help requests activate the session flow, explanations and quotes do not',()=>{
  for(const text of ['Ayúdame en tiempo real','Por favor acompáñame mientras programo','Can you help me in real time'])assert.equal(requestsRealtimeHelp(text),true,text);
  for(const text of ['Explica cómo funciona la ayuda en tiempo real','No me ayudes en tiempo real','"Ayúdame en tiempo real"','```text\nAyúdame en tiempo real\n```','Escribe el código en vivo'])assert.equal(requestsRealtimeHelp(text),false,text);
});

function fixture(options={}){
  let snapshot={path:'main.py',content:'print(41+1)',version:1,workspace:'/project',provider:'fixture',model:'fixture-model',position:{lineNumber:1,column:12}},time=0;
  const calls=[],states=[],scheduled=new Map();let seq=0;
  const api=options.api|| (async(path,body)=>{calls.push({path,body});return path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?{offset:1,delta:'Consejo de prueba',done:true}:{};});
  const session=new CompanionSession({snapshot:()=>({...snapshot}),api,onState:s=>states.push(s),clock:()=>time,delay:(fn,ms)=>{scheduled.set(++seq,{fn,ms});return seq;},clear:id=>scheduled.delete(id),idleMs:100,minInterval:0,...options});
  return {session,calls,states,scheduled,set:value=>Object.assign(snapshot,value),begin:()=>session.begin(snapshot),advance:value=>time+=value};
}
test('No request runs before explicit activation',async()=>{const f=fixture();f.session.changed();await f.session.review();assert.equal(f.calls.length,0);assert.equal(f.scheduled.size,0);});
test('Review sends the actual unsaved buffer to the authorised provider and never writes',async()=>{const f=fixture();f.begin();await f.session.review();assert.equal(f.calls[0].body.content,'print(41+1)');assert.equal(f.calls[0].body.consent,true);assert.equal(f.calls[0].body.model,'fixture-model');assert.equal(f.states.at(-1).text,'Consejo de prueba');assert.ok(f.calls.every(x=>x.path.startsWith('/ai/')));});
test('A late response after stopping is discarded',async()=>{let resolve;const f=fixture({api:async path=>path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?await new Promise(r=>resolve=r):{}});f.begin();const review=f.session.review();await new Promise(r=>setImmediate(r));f.session.stop();resolve({delta:'STALE',offset:1,done:true});await review;assert.ok(!f.states.some(s=>s.text==='STALE'));assert.equal(f.states.at(-1).status,'off');});
test('A revision changed during generation invalidates advice',async()=>{let resolve;const f=fixture({api:async path=>path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?await new Promise(r=>resolve=r):{}});f.begin();const review=f.session.review();await new Promise(r=>setImmediate(r));f.set({content:'print(43)',version:2});f.session.changed();resolve({delta:'STALE',offset:1,done:true});await review;assert.ok(!f.states.some(s=>s.text==='STALE'));assert.equal(f.session.job,null);});
test('Switching project or provider invalidates the grant',async()=>{for(const change of [{workspace:'/other'},{provider:'another'},{model:'another'}]){const f=fixture();f.begin();f.set(change);await f.session.review();assert.equal(f.calls.length,0);assert.equal(f.session.enabled,false);}});
test('Repeated unchanged snapshots do not spend another request',async()=>{const f=fixture();f.begin();await f.session.review();f.session.changed();await f.session.review();assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,1);});
test('Cooldown and request budget remain enforced for explicit prediction',async()=>{const f=fixture({minInterval:20000,maxRequests:2});f.begin();await f.session.review();await f.session.review(true);assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,1);assert.ok([...f.scheduled.values()].some(t=>t.ms===20000));f.advance(20000);await f.session.review(true);f.advance(20000);await f.session.review(true);assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,2);assert.equal(f.session.enabled,false);assert.equal(f.states.at(-1).status,'limit');});
test('Restart after stopping the same buffer works, and oversized buffers are rejected',async()=>{const f=fixture();f.begin();await f.session.review();f.session.stop();f.begin();await f.session.review();assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,2);f.set({content:'x'.repeat(64001),version:2});await f.session.review();assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,2);assert.equal(f.states.at(-1).status,'error');f.session.dispose();assert.equal(f.scheduled.size,0);});

test('Focus and the real selection guide a review without altering source',async()=>{
 const f=fixture();f.set({focus:'explain',selection:'print(41+1)'});f.begin();await f.session.review();
 assert.match(f.calls[0].body.question,/didáctica/);assert.match(f.calls[0].body.question,/print\(41\+1\)/);
 f.set({focus:'next'});f.session.changed();await f.session.review();assert.equal(f.calls.filter(x=>x.path==='/ai/start').length,2);assert.match(f.calls.at(-2).body.question,/implementación más pequeño/);
});
test('Repeated explicit clicks cannot start overlapping generations or spend the budget twice',async()=>{
 let resolve;const f=fixture({api:async path=>path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?await new Promise(r=>resolve=r):{}});f.begin();const first=f.session.review(true);await new Promise(r=>setImmediate(r));await f.session.review(true);assert.equal(f.session.remaining,11);resolve({delta:'Current',offset:1,done:true});await first;assert.equal(f.states.at(-1).text,'Current');
});
test('An explicit prediction arriving during review is queued once for the same cursor',async()=>{
 let resolve;const f=fixture({api:async path=>path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?await new Promise(r=>resolve=r):{}});f.begin();const first=f.session.review();await new Promise(r=>setImmediate(r));await f.session.review(true);await f.session.review(true);assert.equal(f.session.remaining,11);resolve({delta:'Review',offset:1,done:true});await first;const scheduled=[...f.scheduled.values()].filter(x=>x.ms===0);assert.equal(scheduled.length,1);const prediction=scheduled[0].fn();await new Promise(r=>setImmediate(r));assert.equal(f.session.remaining,10);resolve({delta:'Prediction',offset:1,done:true});await prediction;assert.equal(f.states.at(-1).prediction,true);
});
test('Moving the cursor during prediction discards the continuation without invalidating a normal review',async()=>{
 for(const prediction of [true,false]){let resolve;const f=fixture({api:async path=>path==='/ai/start'?{id:'job'}:path.startsWith('/ai/job')?await new Promise(r=>resolve=r):{}});f.begin();const review=f.session.review(prediction);await new Promise(r=>setImmediate(r));f.set({position:{lineNumber:1,column:4}});f.session.changed();resolve({delta:'Cursor owned',offset:1,done:true});await review;assert.equal(f.states.some(s=>s.text==='Cursor owned'),!prediction);}
});
