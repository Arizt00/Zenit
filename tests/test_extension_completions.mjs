import test from 'node:test';import assert from 'node:assert/strict';
import {monacoCompletion,completionDetails,completionProviders} from '../web/src/extension-completions.js';
const options={monaco:{languages:{CompletionItemKind:{Text:18,Function:1,Variable:4},CompletionItemInsertTextRule:{InsertAsSnippet:4}}},mapRange:r=>r?['range',r.start.line,r.start.character,r.end.line,r.end.character]:undefined,range:['default']};
test('extension function kinds use Monaco values and structured labels insert only their label',()=>{
 const result=monacoCompletion({label:{label:'renderFloat',detail:'(float)'},kind:2},options);assert.equal(result.kind,1);assert.equal(result.insertText,'renderFloat');assert.deepEqual(result.range,['default']);
});
test('snippet and insert/replace ranges survive conversion without mutating the source',()=>{
 const range={start:{line:0,character:0},end:{line:0,character:3}},item={label:'value',kind:5,insertText:{value:'${1:value}'},range:{inserting:range,replacing:range},documentation:{value:'docs',isTrusted:true}};
 const result=monacoCompletion(item,options);assert.equal(result.kind,4);assert.equal(result.insertTextRules,4);assert.deepEqual(result.range.insert,['range',0,0,0,3]);assert.equal(result.documentation.isTrusted,false);assert.equal(item.documentation.isTrusted,true);
});
test('lazy resolution cannot change primary edits or sorting but can add safe documentation',()=>{
 const initial=monacoCompletion({label:'value',kind:5,insertText:{value:'${1:value}'},sortText:'a'},options);
 const resolved=completionDetails(initial,{label:'bad',kind:2,insertText:'bad',sortText:'z',documentation:{value:'details',isTrusted:true},detail:'native'},options);
 assert.equal(resolved.kind,4);assert.equal(resolved.label,'value');assert.equal(resolved.insertText,'${1:value}');assert.equal(resolved.insertTextRules,4);assert.equal(resolved.sortText,'a');assert.deepEqual(resolved.range,initial.range);assert.equal(resolved.documentation.isTrusted,false);assert.equal(resolved.detail,'native');
});
test('resolving detail preserves existing extra edits when the extension supplies no replacement',()=>{
 const range={start:{line:0,character:0},end:{line:0,character:0}},initial=monacoCompletion({label:'answer',additionalTextEdits:[{range,newText:'import value'}]},options);
 assert.deepEqual(completionDetails(initial,{detail:'documentation only'},options).additionalTextEdits,initial.additionalTextEdits);
});
test('multiple providers in one host produce one editor adapter and retain all trigger characters',()=>{
 const source=[{kind:'completion',language:'nc',triggers:['.']},{kind:'hover',language:'nc'},{kind:'completion',language:'nc',triggers:[':', '.']}];
 const result=completionProviders(source);assert.equal(result.length,2);assert.deepEqual(result[0].triggers,['.',':']);assert.deepEqual(source[0].triggers,['.']);
});
