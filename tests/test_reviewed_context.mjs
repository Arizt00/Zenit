import test from 'node:test';
import assert from 'node:assert/strict';
import {limitReviewedMessage} from '../web/src/experience-r2.js';

test('a short reviewed report reaches the composer unchanged',()=>{
 const text='Ejecución registrada: código 1.\nmain.py: valor no definido.';
 assert.equal(limitReviewedMessage(text),text);
});
test('large reviewed reports stay within every provider question budget and identify omissions',()=>{
 const lead='Hechos: revisión 3; no coincide con el búfer actual.\n';
 const result=limitReviewedMessage(lead+'🪐'.repeat(20000));
 assert.ok(result.length<=15500);assert.ok(result.startsWith(lead));assert.match(result,/se ha omitido contenido/);assert.match(result,/Pide los fragmentos/);
 assert.equal(result.isWellFormed(),true);
});
