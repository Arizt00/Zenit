import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ExtensionServicesUI} from '../web/src/extension-services.js';
test('Auxiliary windows sharing the stream neither open nor acknowledge global controls',async()=>{
 globalThis.location={search:'?panel=project'};let replies=0,opens=0;
 const ui={host:{platform:{api:async()=>replies++},editor:{},studio:{host:{palette:()=>opens++}}}};
 try{await ExtensionServicesUI.prototype.event.call(ui,{command:'zenit.command',request:'one',id:'workbench.action.showCommands'});assert.equal(opens,0);assert.equal(replies,0);}finally{delete globalThis.location;}
});
test('The main workbench opens the actual command control and acknowledges once',async()=>{
 globalThis.location={search:''};const calls=[],replies=[];
 const ui={host:{platform:{api:async(...args)=>replies.push(args)},editor:{},studio:{host:{palette:q=>calls.push(q)}}}};
 try{await ExtensionServicesUI.prototype.event.call(ui,{command:'zenit.command',request:'one',id:'workbench.action.showCommands'});assert.deepEqual(calls,['>']);assert.deepEqual(replies,[['/extensions/pick',{id:'one',value:{ok:true}}]]);}finally{delete globalThis.location;}
});
test('A failed control does not acknowledge success',async()=>{
 globalThis.location={search:''};const replies=[];
 const ui={host:{platform:{api:async(path,body)=>replies.push(body)},editor:{},studio:{host:{palette:()=>{throw Error('Unavailable');}}}}};
 try{await ExtensionServicesUI.prototype.event.call(ui,{command:'zenit.command',request:'one',id:'workbench.action.showCommands'});assert.deepEqual(replies,[{id:'one',value:{ok:false,error:'Unavailable'}}]);}finally{delete globalThis.location;}
});
