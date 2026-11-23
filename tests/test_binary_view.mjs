import test from 'node:test';
import assert from 'node:assert/strict';
import {byteRows,byteValue,binaryPatches} from '../web/src/binary-view.js';
test('Rows preserve offsets, safe ASCII and a partial final row',()=>{const rows=byteRows(Uint8Array.from([0,65,60,255,...Array(14).fill(32)]),512);assert.equal(rows[0].offset,512);assert.equal(rows[0].ascii.slice(0,4),'·A<·');assert.equal(rows[1].offset,528);assert.equal(rows[1].hex.length,2);});
test('Byte interpretation honors endianness and never crosses a page boundary',()=>{const bytes=Uint8Array.from([1,2,3,4]);assert.match(byteValue(bytes,0,true),/u32: 67305985/);assert.match(byteValue(bytes,0,false),/u32: 16909060/);assert.equal(byteValue(bytes,3),'u8: 4');assert.equal(byteValue(bytes,4),'');});

test('Byte patches sort offsets and group only consecutive edits without changing originals',()=>{const patches=new Map([[8,{before:0,after:255}],[2,{before:65,after:66}],[3,{before:90,after:91}]]),result=binaryPatches({patches});assert.deepEqual(result,[{offset:2,before:btoa('AZ'),after:btoa('B[')},{offset:8,before:btoa('\0'),after:btoa('\xff')}]);});
