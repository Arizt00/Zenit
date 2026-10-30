import test from 'node:test';
import assert from 'node:assert/strict';
import {captureLanternBuffers,sameLanternCapture} from '../web/src/lantern-buffers.js';

function editor(){
 const models=new Map([
  ['Main.java',{value:'main',savedValue:'main',model:{getValue:()=> 'main',getVersionId:()=>7}}],
  ['Calculadora.java',{value:'class Calculadora {}',savedValue:''}],
  ['saved.java',{value:'saved',savedValue:'saved'}],
  ['data.bin',{kind:'binary',value:'bytes',savedValue:''}],
  ['.env',{value:'private',savedValue:''}],
  ['build/generated.java',{value:'generated',savedValue:''}],
  ['C:\\outside.java',{value:'external',savedValue:''}]
 ]);
 return {models,current:'Main.java',getValue(){return models.get(this.current).value;},isDirty(name){const row=models.get(name);return row.value!==row.savedValue;}};
}
test('a revision includes unsaved sibling sources and excludes saved, binary, private and external documents',()=>{
 const ed=editor(),snapshot=captureLanternBuffers(ed);
 assert.equal(snapshot.content,'main');assert.equal(snapshot.version,7);
 assert.deepEqual(snapshot.buffers,[{path:'Calculadora.java',content:'class Calculadora {}'}]);
});
test('editing a helper changes a pinned revision without changing its main version',()=>{
 const ed=editor(),before=captureLanternBuffers(ed);ed.current='Calculadora.java';
 assert(sameLanternCapture(before,captureLanternBuffers(ed,'Main.java')));
 ed.models.get('Calculadora.java').value='class Calculadora { int value=42; }';
 const after=captureLanternBuffers(ed,'Main.java');
 assert.equal(after.content,before.content);assert.equal(after.version,before.version);
 assert(!sameLanternCapture(before,after));
 ed.models.get('Calculadora.java').savedValue=ed.models.get('Calculadora.java').value;
 assert.equal(captureLanternBuffers(ed,'Main.java').buffers.length,0);
});
