import test from 'node:test';
import assert from 'node:assert/strict';
import {waitForQtBridge,waitForNativeBridge} from '../web/src/native-ready.js';
function host(ua='QtWebEngine/6.11'){
  const target=new EventTarget();let count=0;
  Object.assign(target,{navigator:{userAgent:ua},setTimeout,clearTimeout,
    addEventListener(...args){count++;EventTarget.prototype.addEventListener.apply(this,args);},
    removeEventListener(...args){count--;EventTarget.prototype.removeEventListener.apply(this,args);}});
  Object.defineProperty(target,'listeners',{get:()=>count});return target;
}
test('Browser startup does not wait for a desktop bridge',async()=>{const h=host('Chrome/140');await waitForQtBridge(h);assert.equal(h.listeners,0);});
test('An already initialized Qt bridge allows Monaco to start immediately',async()=>{const h=host();h.pywebview={api:{status(){}}};await waitForQtBridge(h);assert.equal(h.listeners,0);});
test('Delayed Qt injection completes before the caller installs AMD',async()=>{
  const h=host();let installed=false;const ready=waitForQtBridge(h,1000).then(()=>{installed=true;});
  await Promise.resolve();assert.equal(installed,false);
  h.pywebview={api:{status(){}}};h.dispatchEvent(new Event('pywebviewready'));await ready;assert.equal(installed,true);assert.equal(h.listeners,0);
});
test('Missing bridge rejects and cleans up its event listener',async()=>{const h=host();await assert.rejects(waitForQtBridge(h,10),/no está disponible/);assert.equal(h.listeners,0);});
test('A ready event without the exposed API fails explicitly',async()=>{const h=host();const ready=waitForQtBridge(h);h.dispatchEvent(new Event('pywebviewready'));await assert.rejects(ready,/no expuso/);assert.equal(h.listeners,0);});
test('WebView2 injection finishes before AMD even without a Qt user agent',async()=>{
  const h=host('Edg/142');h.chrome={webview:{}};let amd=false;
  const result=waitForNativeBridge(h,1000).then(()=>{amd=true;});
  await Promise.resolve();assert.equal(amd,false);h.pywebview={api:{status(){}}};h.dispatchEvent(new Event('pywebviewready'));
  await result;assert.equal(amd,true);assert.equal(h.listeners,0);
});
test('The backend desktop marker also gates an unknown native renderer',async()=>{
  const h=host('Unknown desktop');const result=waitForNativeBridge(h,1000,true);
  assert.equal(h.listeners,1);h.pywebview={api:{status(){}}};h.dispatchEvent(new Event('pywebviewready'));await result;assert.equal(h.listeners,0);
});
