import test from 'node:test';
import assert from 'node:assert/strict';
import {melodyContext} from '../web/src/melody-context.js';
test('questions honor no-code, selected code, and whole-file scopes',()=>{
  const data={file:'secret = 123\nprint(secret)',selection:'print(secret)'};
  assert.deepEqual(melodyContext({...data,scope:'none'}),{content:'',kind:'none'});
  assert.deepEqual(melodyContext({...data,scope:'selection'}),{content:'print(secret)',kind:'selection'});
  assert.equal(melodyContext({...data,scope:'file'}).content,data.file);
  assert.equal(melodyContext({...data,selection:'',scope:'selection'}).content,data.file);
});
test('live editing includes the complete file even when question scope is limited',()=>{
  for(const scope of ['none','selection','file'])assert.deepEqual(melodyContext({file:'complete file',selection:'fragment',scope,editing:true}),{content:'complete file',kind:'file'});
});
