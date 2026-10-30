import test from 'node:test';
import assert from 'node:assert/strict';
import {CoCoRunIntents} from '../web/coco-intents.js';

const storage=()=>{const items=new Map();return {getItem:key=>items.get(key),setItem:(key,value)=>items.set(key,value),removeItem:key=>items.delete(key)};};
test('lost acknowledgement survives a tab reload with the same intent, without persisting promises',()=>{
  const disk=storage(),first=new CoCoRunIntents(disk);first.configure('room');first.set('stable-document',{requestId:'participant:intent',promise:Promise.resolve()});
  const restored=new CoCoRunIntents(disk);restored.configure('room');assert.equal(restored.get('stable-document').requestId,'participant:intent');assert.equal(restored.get('stable-document').promise,undefined);
  restored.delete('stable-document');const after=new CoCoRunIntents(disk);after.configure('room');assert.equal(after.get('stable-document'),undefined);
});
test('different rooms do not share pending intents and explicit leave removes them',()=>{
  const disk=storage(),intents=new CoCoRunIntents(disk);intents.configure('room-1');intents.set('document',{requestId:'first'});intents.configure('room-2');assert.equal(intents.get('document'),undefined);intents.set('document',{requestId:'second'});intents.clear();intents.configure('room-2');assert.equal(intents.get('document'),undefined);intents.configure('room-1');assert.equal(intents.get('document').requestId,'first');
});
test('storage failure retains live identities and the memory budget refuses silent eviction',()=>{
  const intents=new CoCoRunIntents({getItem(){throw Error('unavailable');},setItem(){throw Error('full');}});intents.configure('room');for(let i=0;i<128;i++)intents.set('document-'+i,{requestId:'intent-'+i});assert.throws(()=>intents.set('overflow',{requestId:'new'}));assert.equal(intents.get('document-0').requestId,'intent-0');
});
