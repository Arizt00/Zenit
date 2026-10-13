// Every pywebview renderer injects anonymous UMD libraries. WebView2 exposes
// chrome.webview before injection; finish it before Monaco installs AMD.
export function waitForNativeBridge(host=window,timeoutMs=15000,required=false){
  const native=required||host.navigator.userAgent.includes('QtWebEngine')||!!host.chrome?.webview;
  if(!native||typeof host.pywebview?.api?.status==='function')return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const cleanup=()=>{host.clearTimeout(timer);host.removeEventListener('pywebviewready',ready);};
    const ready=()=>{cleanup();if(typeof host.pywebview?.api?.status==='function')resolve();else reject(new Error('El puente nativo no expuso su API.'));};
    const timer=host.setTimeout(()=>{cleanup();reject(new Error('El puente nativo no está disponible. Vuelve a abrir Zénit.'));},timeoutMs);
    host.addEventListener('pywebviewready',ready,{once:true});
  });
}
export const waitForQtBridge=waitForNativeBridge;
