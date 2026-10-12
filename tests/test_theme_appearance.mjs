import test from 'node:test';import assert from 'node:assert/strict';
import {restoreShellAppearance,applyShellTheme} from '../web/src/extension-theme.js';
const root=()=>({dataset:{},style:{values:new Map(),setProperty(k,v){this.values.set(k,v)},getPropertyValue(k){return this.values.get(k)},removeProperty(k){this.values.delete(k)}}});
test('Effective appearance restores safe colours before contributions, and native reset clears it',()=>{
 const values=new Map();globalThis.localStorage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
 const original=root();applyShellTheme({id:'qa:dark',uiTheme:'vs-dark',data:{colors:{'editor.background':'#121212','editor.foreground':'#dddddd'}}},original);
 const restored=root();assert.equal(restoreShellAppearance(restored,localStorage),true);assert.equal(restored.dataset.extensionTheme,'qa:dark');assert.equal(restored.style.values.get('--editor'),'#121212');assert.deepEqual([...restored.style.values],[...original.style.values]);
 applyShellTheme(null,restored,'forest');assert.equal(restored.dataset.theme,'forest');assert.equal(restored.style.values.size,0);assert.equal(restoreShellAppearance(root(),localStorage),false);delete globalThis.localStorage;
});
test('Tampered cached CSS and unknown tokens cannot enter the shell',()=>{
 for(const palette of [{surface:'url(https://example.com)'},{'unknown-token':'#ffffff'},{surface:'#fff'}]){
  const target=root(),storage={getItem:()=>JSON.stringify({id:'qa:dark',base:'dark',palette})};assert.equal(restoreShellAppearance(target,storage),false);assert.equal(target.style.values.size,0);
 }
});
