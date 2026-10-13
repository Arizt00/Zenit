import test from 'node:test';import assert from 'node:assert/strict';
import {validDiagnostics} from '../web/src/language-diagnostics.js';
const valid={message:'An actual diagnostic',range:{start:{line:0,character:2},end:{line:0,character:5}}};
test('Malformed language server records cannot crash marker rendering',()=>{assert.deepEqual(validDiagnostics([null,{},valid,{range:{start:{line:-1,character:0},end:{line:0,character:1}}},{range:{start:{line:1,character:4},end:{line:1,character:1}}}]),[valid]);assert.deepEqual(validDiagnostics({}),[]);});
test('UTF-16 ranges are preserved and the diagnostics batch stays bounded',()=>{assert.equal(validDiagnostics(Array(600).fill(valid)).length,500);assert.equal(validDiagnostics([valid])[0],valid);});
