import test from 'node:test';
import assert from 'node:assert/strict';
import {adviceLines} from '../web/src/melody-companion.js';
test('Advice anchors use bounded, deduplicated actual lines, in Spanish and English',()=>{
 assert.deepEqual(adviceLines('Línea 2; líneas 4–6; L4; lines 8-10; line 200; línea 0',10),[2,4,6,8,10]);assert.deepEqual(adviceLines('No references',10),[]);assert.deepEqual(adviceLines('L1 L2 L3 L4 L5 L6 L7',10),[1,2,3,4,5,6]);
});
