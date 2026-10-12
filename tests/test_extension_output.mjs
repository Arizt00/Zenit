import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const createUI=createRequire(import.meta.url)('../backend/extension_ui.cjs');

test('An explicit channel hide is distinguishable from ordinary writes to an invisible channel',async()=>{
 const f=fixture(),channel=f.v.window.createOutputChannel('Hidden');await Promise.resolve();assert.equal(f.records.at(-1).dismiss,undefined);channel.hide();await Promise.resolve();assert.equal(f.records.at(-1).dismiss,1);assert.equal(f.records.at(-1).visible,false);channel.append('retained');await Promise.resolve();assert.equal(f.records.at(-1).dismiss,1);channel.show(true);await Promise.resolve();assert.equal(f.records.at(-1).reveal,1);assert.equal(f.records.at(-1).preserveFocus,true);
});
function fixture(host){
 class Emitter{constructor(){this.listeners=[];this.event=f=>{this.listeners.push(f);return {dispose:()=>this.listeners.splice(this.listeners.indexOf(f),1)}};}fire(value){for(const f of this.listeners)f(value);}dispose(){this.listeners=[];}}
 const records=[];host ||= {service:async(method,state)=>records.push({method,...structuredClone(state)})};
 const v={EventEmitter:Emitter,Disposable:class{constructor(dispose){this.dispose=dispose;}},window:{},languages:{},LogLevel:{Off:0,Trace:1,Debug:2,Info:3,Warning:4,Error:5}};
 return {v,ui:createUI(v,host),records,host};
}
test('Changing a log level through the UI emits the real event; Off suppresses all log methods',async()=>{
 const f=fixture(),channel=f.v.window.createOutputChannel('Log',{log:true}),events=[];channel.onDidChangeLogLevel(level=>events.push(level));await Promise.resolve();const key=f.records.at(-1).key;
 f.ui.event('output.control',{key,action:'logLevel',level:2});channel.debug('visible');await Promise.resolve();assert.equal(channel.logLevel,2);assert.deepEqual(events,[2]);assert.match(f.records.at(-1).text,/visible/);
 f.ui.event('output.control',{key,action:'logLevel',level:0});channel.clear();for(const method of ['trace','debug','info','warn','error'])channel[method]('must not appear');await Promise.resolve();assert.equal(f.records.at(-1).text,'');assert.deepEqual(events,[2,0]);
});
test('Output and status keys do not collide when an extension and its dependency share a Node host',async()=>{
 const first=fixture(),second=fixture(first.host);first.v.window.createOutputChannel('Parent');second.v.window.createOutputChannel('Dependency');first.v.window.createStatusBarItem('one',1);second.v.window.createStatusBarItem('two',1);await Promise.resolve();assert.equal(new Set(first.records.map(x=>x.key)).size,4);
});
test('Channel clearing is routed only to its owner and disposed channels stay removed',async()=>{
 const f=fixture(),one=f.v.window.createOutputChannel('One','javascript'),two=f.v.window.createOutputChannel('Two');one.appendLine('first');two.appendLine('second');await Promise.resolve();const keys=f.records.map(x=>x.key);f.ui.event('output.control',{key:keys[0],action:'clear'});await Promise.resolve();assert.equal(f.records.at(-1).text,'');assert.equal(f.records.find(x=>x.name==='Two').text,'second\n');one.dispose();one.append('late');f.ui.event('output.control',{key:keys[0],action:'show'});await Promise.resolve();assert.equal(f.records.at(-1).method,'output.dispose');
});
