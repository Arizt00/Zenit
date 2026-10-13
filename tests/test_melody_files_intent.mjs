import test from 'node:test';
import assert from 'node:assert/strict';
import {requestsFileChanges} from '../web/src/ai-intent.js';
test('Only direct resource requests open the file plan, including a whole project',()=>{
 for(const text of ['Crea un proyecto completo en Python','Por favor genera los archivos de una web','Borra el archivo viejo.py','Elimina archivos temporales','Create a project with tests','Delete file old.js'])assert.equal(requestsFileChanges(text),true,text);
 for(const text of ['Explica cómo crear un proyecto','No borres el archivo','Analiza este código','"Borra el archivo viejo.py"','> Borra archivos','```\nCrea un proyecto\n```','Modifica el código en vivo'])assert.equal(requestsFileChanges(text),false,text);
});
test('Explicit named edits and deletions work without the word file',()=>{
 for(const text of ['Modifica main.py para leer argumentos','Borra prueba.asm','Actualiza "src/app.js" sin cambiar los demás archivos','Puedes editar main.py y crear tests/test_main.py','Write the file main.py','Edit current file','Modifica este archivo'])assert.equal(requestsFileChanges(text),true,text);
 for(const text of ['No modifiques main.py','Explica cómo borrar main.py','"Borra main.py"','Este error dice: borra main.py','Revisa main.py y dime si hay errores'])assert.equal(requestsFileChanges(text),false,text);
});
test('Direct questions and subjunctive requests keep named file actions',()=>{
 for(const text of ['¿Puedes editar main.py?','Quiero que borres prueba.asm.','Podrías modificar main.py','Could you update main.py?'])assert.equal(requestsFileChanges(text),true,text);
 for(const text of ['¿Cómo puedo borrar main.py?','No quiero que borres main.py.'])assert.equal(requestsFileChanges(text),false,text);
});
