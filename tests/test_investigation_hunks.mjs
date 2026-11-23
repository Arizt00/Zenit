import test from 'node:test';
import assert from 'node:assert/strict';
import {selectedResearchChanges} from '../web/src/investigations.js';

test('accepting one fragment keeps the rejected fragment and original text intact',()=>{
 const before='a=1\nkeep\nb=2\n',proposal={changes:[{path:'main.py',before,hunks:[{start:0,end:4,before:'a=1\n',text:'a=3\n'},{start:9,end:13,before:'b=2\n',text:'b=4\n'}]}]};
 assert.deepEqual(selectedResearchChanges(proposal,new Set(['0:0'])),[{path:'main.py',before,after:'a=3\nkeep\nb=2\n'}]);assert.equal(proposal.changes[0].before,before);assert.deepEqual(selectedResearchChanges(proposal,new Set()),[]);
});
test('fragments referring to another version are rejected before review',()=>{
 assert.throws(()=>selectedResearchChanges({changes:[{path:'main.py',before:'new source',hunks:[{start:0,end:3,before:'old',text:'fix'}]}]},new Set(['0:0'])),/no coincide/);
});
test('UTF-16 offsets preserve an emoji before an edited line',()=>{
 const before='# 😀\na=1\n',proposal={changes:[{path:'main.py',before,hunks:[{start:5,end:9,before:'a=1\n',text:'a=2\n'}]}]};
 assert.equal(selectedResearchChanges(proposal,new Set(['0:0']))[0].after,'# 😀\na=2\n');
});
