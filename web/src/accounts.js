import {escapeHTML as esc,icon} from './icons.js';
import {providerIcon} from './provider-identity.js';
export const ACCOUNT_PROVIDERS=new Set(['codex','claude-code','gemini-cli','copilot']);
export function accountPanel(platform,provider){
  if(!ACCOUNT_PROVIDERS.has(provider))return '';
  const name={codex:'ChatGPT · Codex','claude-code':'Claude Code','gemini-cli':'Gemini CLI',copilot:'GitHub Copilot'}[provider];
  return `<section class="account-connection" data-account-provider="${provider}" data-status="checking"><header class="account-heading"><span class="account-provider-mark">${providerIcon(provider)}</span><div><span class="platform-eyebrow">MELODY · ${esc(name)}</span><h4>Connect your account.</h4></div></header><p>Continue with official sign-in for ${esc(name)}. Your session remains in its client.</p><div id="account-status" role="status">Checking client…</div><div class="account-actions"><button class="primary-button" id="account-login" disabled>Sign in${icon('arrow-up-right')}</button><button class="secondary-button" id="account-refresh">${icon('refresh')}Check</button>${provider==='codex'?'<button class="text-button" id="account-logout">Sign out of Zénit</button>':''}</div><div id="account-next"></div><details class="account-details"><summary>${icon('shield')}How the connection works</summary><small>Models and limits depend on your plan and official client. Text and code only; proposals are reviewed in Zénit. No credentials are copied into the project.</small></details></section>`;
}
export function bindAccount(platform){
  const root=document.querySelector('.account-connection');if(!root)return;
  const provider=root.dataset.accountProvider;
  const status=root.querySelector('#account-status');
  const next=root.querySelector('#account-next');
  const refresh=async()=>{
    status.textContent='Checking official client…';
    try{
      const state=await platform.api('/ai/account?provider='+provider);if(!root.isConnected)return;
      platform.connectionStates ||= new Map();platform.connectionStates.set(provider,state);document.dispatchEvent(new Event('zenit:provider-state'));
      root.dataset.status=!state.installed?'missing':state.authenticated===true?'connected':state.authenticated===false?'ready':'unverified';
      status.textContent=!state.installed?'Install the official client to continue':state.authenticated===true?`Verified account${state.account?' · '+state.account:''}${state.plan?' · '+state.plan:''}`:state.authenticated===false?'Client ready · sign in':'Client installed · access not yet verified';
      root.querySelector('#account-login').disabled=!state.installed;
      if(!state.installed)next.innerHTML=`<a class="secondary-button" href="${esc(state.docs)}" target="_blank" rel="noopener noreferrer">Install official client ${icon('arrow-up-right')}</a><p>After installation, check the connection. No API key is needed.</p>`;
      else if(!next.querySelector('[data-login-url]'))next.textContent=state.note||'The session remains in the official client’s store.';
      root.querySelector('#account-login').textContent=state.authenticated===true?platform.t('Cambiar de cuenta','Switch account'):platform.t('Sign in','Sign in');
      root.querySelector('#account-logout')?.toggleAttribute('disabled',state.authenticated!==true);
    }catch(error){root.dataset.status='error';status.textContent=error.message;}
  };
  root.querySelector('#account-refresh').onclick=()=>platform.safe(refresh);
  root.querySelector('#account-login').onclick=()=>platform.safe(async()=>{
    const button=root.querySelector('#account-login');button.disabled=true;status.textContent='Opening official sign-in…';
    try{
      const result=await platform.api('/ai/account/login',{provider});
      if(result.mode==='browser'){
        next.innerHTML=`<a class="secondary-button" data-login-url href="${esc(result.url)}" target="_blank" rel="noopener noreferrer">Continue in browser ${icon('arrow-up-right')}</a><p>Complete sign-in and return here. Zénit will check the session.</p>`;
        status.textContent='Waiting for browser authorization';
        root.dataset.status='waiting';
        let checks=0;const check=async()=>{if(!root.isConnected||checks++>=60)return;const s=await platform.api('/ai/account?provider='+provider);if(s.authenticated){next.replaceChildren();await refresh();return;}platform.later(()=>platform.safe(check),2500);};platform.later(()=>platform.safe(check),2500);
      }else{
        platform.host.closeModal();platform.closePage();await platform.attachTerminal(result);
        platform.host.notify('Complete sign-in in the integrated terminal. Then fetch models in Settings → Artificial intelligence.', 'info',10000);
      }
    }finally{button.disabled=false;}
  });
  const logout=root.querySelector('#account-logout');if(logout)logout.onclick=()=>platform.safe(async()=>{await platform.api('/ai/account/logout',{provider});await platform.savePreference('ai.model','');await refresh();});
  platform.safe(refresh);
}
