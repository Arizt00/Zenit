import test from 'node:test';
import assert from 'node:assert/strict';
import {backendRows,machineReport} from '../web/src/performance-report.js';
import {journeySummary} from '../web/src/language-verification.js';
test('backend report preserves overlapping spans instead of subtracting unrelated clocks',()=>{
 assert.deepEqual(backendRows({phases:[{name:'parent',startMs:0,durationMs:30,status:'completed',kind:'startup'},{name:'child',startMs:5,durationMs:10,status:'failed',kind:'optional'}]}).map(r=>[r.start,r.duration,r.status]),[[0,30,'completed'],[5,10,'failed']]);
 assert.deepEqual(backendRows(),[]);
});
test('a missing or stale behavior report is never described as verified',()=>{
 assert.match(journeySummary(null),/Sin recorrido/);assert.match(journeySummary({steps:[{status:'passed'},{status:'missing'}]},false),/1 de 6/);
 assert.match(journeySummary({steps:Array(6).fill({status:'passed'})},true),/Resultado anterior/);
});
test('machine report shows actual RAM and observed guest milestones without certifying SSH acceleration',()=>{
 const html=machineReport({name:'Guest',memoryMiB:1536,cpus:2,acceleration:{preferred:'whpx'},phases:[],guest:{phases:[{name:'shell-prompt',ms:24000}]}});
 assert.match(html,/1536 MiB/);assert.match(html,/Intérprete preparado/);
 const ssh=machineReport({name:'Remote',kind:'ssh',phases:[]});assert.match(ssh,/No se ha medido el arranque/);assert.ok(!ssh.includes('hardware seleccionada'));
 assert.ok(machineReport({name:'<script>',acceleration:{hardware:[{name:'whpx',available:false,reason:'<img>'}]}}).includes('&lt;img&gt;'));
});
