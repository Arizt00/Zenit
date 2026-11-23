import test from 'node:test';
import assert from 'node:assert/strict';
import {NavigationHistory,projectURI} from '../web/src/navigation-state.js';
import {changeExcerpt,ReviewedEdits} from '../web/src/reviewed-edits.js';
import {editingProvider} from '../web/src/extension-editing.js';

test('deleting a folder removes its navigation entries without losing the surviving position',()=>{
 const h=new NavigationHistory();for(const path of ['old/a.py','keep.py','old/b.py'])h.push({path,line:1,column:1});h.removePaths(['old']);assert.deepEqual(h.rows.map(r=>r.path),['keep.py']);assert.equal(h.index,0);h.removePaths(['keep.py']);assert.equal(h.index,-1);assert.equal(h.move(-1),null);
});

test('navigation retains exact locations, branches and is bounded',()=>{
 const history=new NavigationHistory(3);history.push({path:'a.py',line:1,column:2});history.push({path:'b.py',line:9,column:4});
 assert.equal(history.move(-1).path,'a.py');history.push({path:'c.py',line:4,column:7});assert.equal(history.move(1),null);
 history.push({path:'d.py',line:1,column:1});history.push({path:'e.py',line:1,column:1});assert.equal(history.rows.length,3);assert.equal(history.move(-1).path,'d.py');
});
test('review excerpt is bounded and separates unchanged context from edits',()=>{
 const text=changeExcerpt('before\nold\nend','before\nnew\nend');assert.match(text,/− old/);assert.match(text,/\+ new/);assert.ok(changeExcerpt('x\n'.repeat(20000),'y\n'.repeat(20000)).length<=16000);
});
test('Windows file navigation tolerates drive case and rejects escape paths',()=>{
 assert.equal(projectURI('file:///C:/Project%20One','file:///c:/Project%20One/lib/value.py'),'lib/value.py');
 assert.equal(projectURI('file:///C:/Project','file:///C:/Project/../secret.py'),null);
 assert.equal(projectURI('file:///home/Project','file:///home/project/x.py'),null);
});
test('reviewed edits keep absolute URIs inside ordinary project files',()=>{
 const edits=new ReviewedEdits({service:()=>({workspace:'C:\\Project One'})});
 assert.equal(edits.uriPath('file:///c:/Project%20One/src/a.py'),'src/a.py');
 for(const uri of ['file:///C:/Project%20One/.git/config','file:///C:/Project%20One/.lumen/state.json','file:///C:/outside/a.py','../outside.py'])assert.throws(()=>edits.uriPath(uri));
 const history=new NavigationHistory();history.push({path:'a.py',line:3,column:2});history.replace({path:null});assert.equal(history.rows[0].path,'a.py');
});
test('extension highlights preserve text, read and write categories in Monaco',async()=>{
 const ranges=[0,1,2].map(kind=>({range:{start:{line:0,character:kind},end:{line:0,character:kind+1}},kind}));
 const provider=editingProvider({id:'qa.highlight'},{kind:'highlights',language:'python'},{m:{languages:{registerDocumentHighlightProvider:(_,provider)=>provider}},ed:{},call:async()=>ranges,mr:r=>r,host:{}});
 const rows=await provider.provideDocumentHighlights({getVersionId:()=>1,isDisposed:()=>false},{lineNumber:1,column:1});assert.deepEqual(rows.map(r=>r.kind),[0,1,2]);
});
