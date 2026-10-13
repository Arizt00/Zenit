/* Runs before module imports, so missing modules also leave a useful screen. */
(() => {
  const started=performance.now(),phases=[];
  let complete=false,failed=false;
  const labels={shell:['Preparando tu espacio','Preparing your space'],service:['Conectando con Zénit','Connecting to Zénit'],native:['Conectando la ventana','Connecting the window'],editor:['Preparando el editor','Preparing the editor'],extensions:['Cargando tus herramientas','Loading your tools'],welcome:['Abriendo tu espacio','Opening your space']};
  const english=()=>document.documentElement.lang==='en';
  const phase=name=>{
    if(complete||failed)return;
    phases.push({name,ms:Math.round(performance.now()-started)});
    const text=document.getElementById('startup-status');
    if(text)text.textContent=(labels[name]||labels.shell)[english()?1:0];
  };
  const fail=error=>{
    if(complete||failed)return;
    failed=true;
    document.documentElement.removeAttribute('data-booting');
    document.getElementById('startup-screen')?.setAttribute('hidden','');
    const overlay=document.getElementById('connection-overlay');
    if(overlay){overlay.classList.remove('hidden');overlay.querySelector('h1').textContent=english()?'Zénit could not finish opening':'Zénit no pudo terminar de abrirse';overlay.querySelector('p').textContent=String(error?.message||error||'Error de carga');const retry=overlay.querySelector('button');retry.textContent=english()?'Retry':'Volver a intentar';retry.onclick=()=>location.reload();}
  };
  const ready=()=>{complete=true;phases.push({name:'ready',ms:Math.round(performance.now()-started)});document.documentElement.removeAttribute('data-booting');document.getElementById('startup-screen')?.setAttribute('hidden','');cleanup();};
  const onError=event=>{if(event.target?.tagName==='SCRIPT'&&event.target.type==='module')fail(new Error(english()?'A required interface module could not load. Retry opening Zénit.':'No se pudo cargar un módulo de la interfaz. Vuelve a abrir Zénit.'));else if(event.error)fail(event.error);};
  const onRejection=event=>fail(event.reason);
  const cleanup=()=>{window.removeEventListener('error',onError,true);window.removeEventListener('unhandledrejection',onRejection);};
  window.addEventListener('error',onError,true);window.addEventListener('unhandledrejection',onRejection);
  window.zenitStartup={phase,fail,ready,snapshot:()=>({complete,failed,phases:phases.map(p=>({...p}))})};
  phase('shell');
})();
