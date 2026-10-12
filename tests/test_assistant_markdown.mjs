import {test} from 'node:test';
import assert from 'node:assert/strict';
import {markdownBlocks} from '../web/src/assistant-markdown.js';
test('GFM table retains source values, escaped pipes, headings and inline text',()=>{
 const blocks=markdownBlocks('### Medidas\n\n| Campo | Bytes |\n| :--- | ---: |\n| Sal | 16 |\n| Nota \\| extra | 4 |\n\n**Datos reales** y `código`.');
 assert.deepEqual(blocks,[{kind:'heading',level:3,text:'Medidas'},{kind:'table',header:['Campo','Bytes'],rows:[['Sal','16'],['Nota | extra','4']]},{kind:'paragraph',text:'**Datos reales** y `código`.'}]);
});
test('Fences preserve spaces and HTML literally; incomplete streaming fence remains code',()=>{
 assert.deepEqual(markdownBlocks('```html\n  <script>alert(1)</script>\n\n```')[0],{kind:'code',language:'html',text:'  <script>alert(1)</script>\n'});
 assert.deepEqual(markdownBlocks('~~~python\n  print(42)')[0],{kind:'code',language:'python',text:'  print(42)'});
});
test('Lists and quotes preserve content and large responses fall back without truncation',()=>{
 assert.deepEqual(markdownBlocks('3. Primero\n4. Segundo\n\n> una cita'),[{kind:'list',ordered:true,start:3,items:['Primero','Segundo']},{kind:'quote',text:'una cita'}]);
 const text='a\n'.repeat(5001);assert.equal(markdownBlocks(text)[0].text,text);
});
