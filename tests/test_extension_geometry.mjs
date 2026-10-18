import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const createAPI=createRequire(import.meta.url)('../backend/extension_api.cjs');
test('VS Code positions, reversed selections and range overloads preserve document coordinates',()=>{
 const storage=mkdtempSync(join(tmpdir(),'zenit-geometry-'));
 try{
  const {Position:P,Range:R,Selection:S,SemanticTokensBuilder:B,SemanticTokensLegend:L}=createAPI({registerCommand:()=>({dispose(){}}),register:()=>({dispose(){}}),notify(){},effect(){},execute(){}},{id:'qa.geometry',manifest:{},root:storage,workspace:storage,storage,extensions:[]}).vscode;
  const p=new P(3,8);assert.equal(p.with({}),p);assert.equal(p.with({character:2}).character,2);assert.deepEqual([p.translate({lineDelta:-2,characterDelta:1}).line,p.translate(-2,1).character],[1,9]);assert.ok(p.isAfterOrEqual(new P(3,8)));assert.throws(()=>p.translate(-4,0));assert.throws(()=>new P(0,-1));
  const reversed=new R(5,8,2,4);assert.deepEqual([reversed.start.line,reversed.start.character,reversed.end.line,reversed.end.character],[2,4,5,8]);assert.ok(reversed.contains(new P(4,0)));assert.ok(reversed.contains(new R(3,0,5,8)));assert.equal(reversed.intersection(new R(6,0,7,0)),undefined);assert.ok(reversed.intersection(new R(5,8,7,0)).isEmpty);assert.equal(reversed.union(new R(0,0,0,1)).start.line,0);assert.equal(reversed.with({}),reversed);
  const selection=new S(new P(5,8),new P(2,4));assert.ok(selection instanceof R);assert.ok(selection.isReversed);assert.equal(selection.anchor.line,5);assert.equal(selection.active.line,2);assert.equal(selection.start.line,2);
  const builder=new B(new L(['variable'],[]));builder.push(new R(2,4,2,9),'variable',[]);assert.deepEqual([...builder.build().data],[2,4,5,0,0]);
 }finally{rmSync(storage,{recursive:true,force:true});}
});
