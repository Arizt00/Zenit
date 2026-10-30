import test from 'node:test';import assert from 'node:assert/strict';
import {reproductionStatus} from '../web/src/investigation-results.js';
test('two repeated failures are never displayed as passed tests',()=>{
 assert.equal(reproductionStatus({stable:true,runs:[{complete:true,code:1,tests:{summary:{failed:1}}},{complete:true,code:1,tests:{summary:{failed:1}}}]}),'failed');
});
test('matching program output is separated from actual successful assertions',()=>{
 const run={complete:true,code:0};assert.equal(reproductionStatus({stable:true,runs:[run,run]}),'repeated');
 const passed={...run,tests:{summary:{passed:1}}};assert.equal(reproductionStatus({stable:true,runs:[passed,passed]}),'passed');
});
test('incomplete execution and differing results cannot appear verified',()=>{
 assert.equal(reproductionStatus({stable:false,runs:[{complete:true,code:0},{complete:true,code:0}]}),'different');assert.equal(reproductionStatus({stable:true,runs:[{complete:false,code:0},{complete:true,code:0}]}),'incomplete');
});
