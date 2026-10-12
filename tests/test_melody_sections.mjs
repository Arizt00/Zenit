import test from 'node:test';import assert from 'node:assert/strict';
import {adviceSections} from '../web/src/melody-companion.js';
test('Sections preserve actual advice and prefix, without generating conclusions',()=>{
 const text='Nota del proveedor.\n**Observación:** Línea 2 recibe datos.\nRazón: Puede estar vacío.\nPróximo paso: Valida la entrada.\nPrueba: Usa una lista vacía.';assert.deepEqual(adviceSections(text),[{title:'',body:'Nota del proveedor.'},{title:'Observación',body:'Línea 2 recibe datos.'},{title:'Razón',body:'Puede estar vacío.'},{title:'Próximo paso',body:'Valida la entrada.'},{title:'Prueba',body:'Usa una lista vacía.'}]);
});
test('Unstructured or single-section answers retain the existing plain text flow',()=>{
 assert.deepEqual(adviceSections('Consejo libre sin apartados.'),[]);assert.deepEqual(adviceSections('Observación: Un único dato.'),[]);
});
