import {escapeHTML as esc,icon} from './icons.js';
export const ACCOUNT_PROVIDERS=new Set(['codex','claude-code','gemini-cli','copilot']);
export function accountPanel(platform,provider){
  if(!ACCOUNT_PROVIDERS.has(provider))return '';
  const name={codex:'ChatGPT · Codex','claude-code':'Claude Code','gemini-cli':'Gemini CLI',copilot:'GitHub Copilot'}[provider];
  return `<section class="account-connection" data-account-provider="${provider}" data-status="checking"><header class="account-heading"><span class="account-provider-mark">${icon('sparkles')}</span><div><span class="platform-eyebrow">MELODY · ${esc(name)}</span><h4>Conecta tu cuenta.</h4></div></header><p>Continúa con el acceso oficial de ${esc(name)}. Tu sesión permanece en su cliente.</p><div id="account-status" role="status">Comprobando el cliente…</div><div class="account-actions"><button class="primary-button" id="account-login" disabled>Iniciar sesión${icon('arrow-up-right')}</button><button class="secondary-button" id="account-refresh">${icon('refresh')}Comprobar</button>${provider==='codex'?'<button class="text-button" id="account-logout">Cerrar sesión de Zénit</button>':''}</div><div id="account-next"></div><details class="account-details"><summary>${icon('shield')}Cómo funciona la conexión</summary><small>Los modelos y límites disponibles dependen de tu plan y del cliente oficial. Solo texto y código; las propuestas se revisan en Zénit. No necesitas copiar credenciales al proyecto.</small></details></section>`;
}
export function bindAccount(platform){
  const root=document.querySelector('.account-connection');if(!root)return;
  const provider=root.dataset.accountProvider;
  const status=root.querySelector('#account-status');
  const next=root.querySelector('#account-next');
  const refresh=async()=>{
    status.textContent='Comprobando el cliente oficial…';
    try{
      const state=await platform.api('/ai/account?provider='+provider);if(!root.isConnected)return;
      root.dataset.status=!state.installed?'missing':state.authenticated===true?'connected':state.authenticated===false?'ready':'unverified';
      status.textContent=!state.installed?'Cliente oficial pendiente de instalar':state.authenticated===true?`Sesión verificada${state.account?' · '+state.account:''}${state.plan?' · '+state.plan:''}`:state.authenticated===false?'Cliente listo · inicia sesión':'Cliente instalado · acceso pendiente de verificar';
      root.querySelector('#account-login').disabled=!state.installed;
      if(!state.installed)next.innerHTML=`<a class="secondary-button" href="${esc(state.docs)}" target="_blank" rel="noopener noreferrer">Instalar el cliente oficial ${icon('arrow-up-right')}</a><p>Después de instalarlo, pulsa Comprobar conexión. No necesitas una clave de API.</p>`;
      else if(!next.querySelector('[data-login-url]'))next.textContent=state.note||'La sesión permanece en el almacén del cliente oficial.';
      if(state.authenticated===true&&provider!=='copilot')root.querySelector('#account-login').textContent='Cambiar de cuenta';
    }catch(error){root.dataset.status='error';status.textContent=error.message;}
  };
  root.querySelector('#account-refresh').onclick=()=>platform.safe(refresh);
  root.querySelector('#account-login').onclick=()=>platform.safe(async()=>{
    const button=root.querySelector('#account-login');button.disabled=true;status.textContent='Abriendo el acceso oficial…';
    try{
      const result=await platform.api('/ai/account/login',{provider});
      if(result.mode==='browser'){
        next.innerHTML=`<a class="secondary-button" data-login-url href="${esc(result.url)}" target="_blank" rel="noopener noreferrer">Continuar en el navegador ${icon('arrow-up-right')}</a><p>Completa el acceso y vuelve aquí. Zénit comprobará la sesión.</p>`;
        status.textContent='Esperando autorización en el navegador';
        root.dataset.status='waiting';
        let checks=0;const check=async()=>{if(!root.isConnected||checks++>=60)return;const s=await platform.api('/ai/account?provider='+provider);if(s.authenticated){next.replaceChildren();await refresh();return;}platform.later(()=>platform.safe(check),2500);};platform.later(()=>platform.safe(check),2500);
      }else{
        platform.host.closeModal();platform.closePage();await platform.attachTerminal(result);
        platform.host.notify('Completa el acceso en la terminal integrada. Después consulta los modelos en Ajustes → Inteligencia artificial.', 'info',10000);
      }
    }finally{button.disabled=false;}
  });
  const logout=root.querySelector('#account-logout');if(logout)logout.onclick=()=>platform.safe(async()=>{await platform.api('/ai/account/logout',{provider});await refresh();});
  platform.safe(refresh);
}
