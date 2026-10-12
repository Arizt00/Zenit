import test from 'node:test';
import assert from 'node:assert/strict';
import {requestsFileChanges} from '../web/src/ai-intent.js';
test('Only direct resource requests open the file plan, including a whole project',()=>{
 for(const text of ['Crea un proyecto completo en Python','Por favor genera los archivos de una web','Borra el archivo viejo.py','Elimina archivos temporales','Create a project with tests','Delete file old.js'])assert.equal(requestsFileChanges(text),true,text);
 for(const text of ['Explica cómo crear un proyecto','No borres el archivo','Analiza este código','"Borra el archivo viejo.py"','> Borra archivos','```\nCrea un proyecto\n```','Modifica el código en vivo'])assert.equal(requestsFileChanges(text),false,text);
});
