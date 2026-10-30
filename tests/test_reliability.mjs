import test from 'node:test';
import assert from 'node:assert/strict';
import {captureBinary,restoreBinary} from '../web/src/binary-view.js';
import {evidenceLabel,renderExecutionEvidence} from '../web/src/execution-evidence.js';
import {timingRows} from '../web/src/performance-report.js';

test('pending bytes on several pages round trip with undo and original revision',()=>{
 const original={revision:'disk-1',binaryState:{revision:'disk-1',patches:new Map([[8193,{before:1,after:255}],[17,{before:3,after:4}],[18,{before:7,after:9}]]),undo:[],redo:[]}};
 const recovery=captureBinary(original,8192),restored={revision:'disk-1'};
 assert.equal(recovery.patches.length,2);assert.equal(restoreBinary(restored,recovery),true);
 assert.deepEqual(captureBinary(restored,8192),recovery);assert.equal(restored.binaryState.undo.length,3);
 const changed={revision:'disk-2'};assert.equal(restoreBinary(changed,recovery),false);
 assert.equal(changed.recoveryConflict,true);assert.equal(changed.binaryState.revision,'disk-1');assert.equal(changed.binaryState.patches.get(8193).after,255);
});

test('evidence distinguishes changed dependencies from matching main source and escapes data',()=>{
 const run={matchesBuffer:true,matchesTarget:true,matchesEnvironment:true,complete:true,contextVerification:{status:'changed',notice:'<script>',changed:['<img>']},commands:[['evil','<svg>']]};
 assert.equal(evidenceLabel(run),'Dependencias modificadas');
 assert.ok(!renderExecutionEvidence(run).includes('<script>'));assert.ok(renderExecutionEvidence(run).includes('&lt;svg&gt;'));
 assert.equal(evidenceLabel({...run,currentEvidence:true}),'Contexto revisado');
 assert.equal(evidenceLabel({...run,matchesTarget:false}),'Otro destino');
 assert.equal(evidenceLabel({...run,matchesEnvironment:false}),'Otro entorno');
 assert.equal(evidenceLabel(null),'Sin evidencia');
});

test('startup report separates cumulative milestones and phase duration',()=>{
 const rows=timingRows({phases:[{name:'shell',ms:0},{name:'editor',ms:75},{name:'ready',ms:420}]});
 assert.deepEqual(rows.map(r=>r.duration),[0,75,345]);assert.equal(rows[2].label,'Editor disponible');
 assert.deepEqual(timingRows(),[]);
});
