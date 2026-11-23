import test from 'node:test';import assert from 'node:assert/strict';
import {focusedContext} from '../web/src/focused-context.js';
test('Large file context is bounded and contains the cursor, diagnostics and named code without claiming completeness',()=>{
 const rows=Array.from({length:10000},(_,i)=>`const value_${i} = ${i};`);rows[7400]='function calculate_invoice(){ return 42; }';
 const text=rows.join('\n'),result=focusedContext({text,question:'Explica calculate_invoice',line:4200,diagnostics:[{line:9100}]});
 assert.ok(result.partial);assert.ok(result.content.length<64000);assert.match(result.content,/CONTEXTO PARCIAL/);assert.match(result.content,/calculate_invoice/);assert.match(result.content,/value_4199/);assert.match(result.content,/value_9099/);assert.ok(!result.content.includes('value_5500 '));assert.equal(rows.length,10000);
});
test('Short context remains exact and a single huge Unicode line remains explicitly partial',()=>{
 assert.equal(focusedContext({text:'print(42)\n'}).content,'print(42)\n');const value=focusedContext({text:'🪐'.repeat(50000)});assert.ok(value.partial);assert.ok(value.content.length<=56000);assert.ok(!/[\uD800-\uDBFF]$/.test(value.content));
});
