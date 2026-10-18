import test from 'node:test';
import assert from 'node:assert/strict';
import {MelodyStream} from '../web/src/melody-stream.js';
test('Melody pauses display work in hidden windows, resumes latest text and respects reader position',()=>{
 const saved=Object.fromEntries(['document','requestAnimationFrame','cancelAnimationFrame','matchMedia'].map(k=>[k,globalThis[k]]));
 const doc=new EventTarget();doc.hidden=false;doc.documentElement={dataset:{}};doc.createTextNode=()=>({data:'',appendData(text){this.data+=text;}});globalThis.document=doc;globalThis.matchMedia=()=>({matches:false});
 let id=0,time=performance.now();const frames=new Map();globalThis.requestAnimationFrame=f=>{frames.set(++id,f);return id;};globalThis.cancelAnimationFrame=i=>frames.delete(i);
 const scroll=new EventTarget();Object.assign(scroll,{scrollTop:0,scrollHeight:1000,clientHeight:200});const element={isConnected:true,replaceChildren(node){this.node=node;}};const stream=new MelodyStream(element,scroll);
 const tick=()=>{const callbacks=[...frames.values()];frames.clear();time+=16;for(const f of callbacks)f(time);};
 try{
  stream.update('Hola 🪐 '.repeat(50));tick();assert.ok(element.node.data.length>0);assert.ok(element.node.data.length<stream.target.length);
  doc.hidden=true;doc.dispatchEvent(new Event('visibilitychange'));assert.equal(frames.size,0);const shown=element.node.data;stream.update('Hola 🪐 '.repeat(100));assert.equal(element.node.data,shown);assert.equal(frames.size,0);
  scroll.scrollTop=20;scroll.dispatchEvent(new Event('scroll'));doc.hidden=false;doc.dispatchEvent(new Event('visibilitychange'));assert.equal(frames.size,1);for(let i=0;i<100;i++)tick();assert.equal(element.node.data,stream.target);assert.equal(scroll.scrollTop,20);
  stream.update('Respuesta nueva');tick();stream.finish();assert.equal(element.node.data,'Respuesta nueva');stream.dispose();doc.dispatchEvent(new Event('visibilitychange'));assert.equal(frames.size,0);
 }finally{for(const [k,v] of Object.entries(saved))if(v===undefined)delete globalThis[k];else globalThis[k]=v;}
});
