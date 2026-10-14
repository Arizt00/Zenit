import {icon,escapeHTML as esc} from './icons.js';
import {providerIcon,providerName} from './provider-identity.js';
const PROVIDERS=['codex','claude-code','gemini-cli','copilot','emma','ollama','openai','anthropic','gemini'];
/** Inline, real provider catalogs; opening the picker never navigates to Settings. */
export function installModelPicker(p,destination){
  const panel=document.createElement('section');panel.id='melody-model-picker';panel.className='melody-model-picker';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Melody models');
  panel.innerHTML=`<header><strong>${icon('sparkles')}Melody models</strong><button type="button" class="icon-button" data-model-close aria-label="Close model picker">${icon('close')}</button></header><label>Provider<select data-model-provider>${PROVIDERS.map(id=>`<option value="${id}">${providerName(id)}</option>`).join('')}</select></label><div class="model-picker-tools"><input data-model-search type="search" placeholder="Find a model…" aria-label="Find a model"><button type="button" class="icon-button" data-model-refresh title="Refresh models">${icon('refresh')}</button></div><p data-model-status role="status"></p><div class="model-picker-list" role="group" aria-label="Available models"></div><footer><button type="button" class="text-button" data-model-account>${icon('settings')}Manage account</button><small>Account access determines availability</small></footer>`;
  document.getElementById('assistant-panel').append(panel);
  const title=document.querySelector('.assistant-heading-title h2'),provider=panel.querySelector('select'),search=panel.querySelector('[data-model-search]'),list=panel.querySelector('.model-picker-list'),status=panel.querySelector('[data-model-status]'),cache=new Map();let epoch=0,anchor=title,closing=false;
  const busy=()=>p.aiStarting||p.aiJob;
  const close=()=>{
    if(closing||panel.hidden)return;const run=++epoch;closing=true;panel.inert=true;panel.setAttribute('aria-hidden','true');
    for(const b of [title,destination])b.setAttribute('aria-expanded','false');
    const style=getComputedStyle(panel),animation=p.host.motion.play(panel,[{opacity:style.opacity,scale:style.scale==='none'?'1':style.scale},{opacity:0,scale:'.985'}],150);
    const finish=()=>{if(closing&&epoch===run){panel.hidden=true;panel.inert=false;panel.removeAttribute('aria-hidden');closing=false;}};
    if(animation)animation.finished.catch(()=>{}).then(finish);else finish();
  };
  const render=models=>{const query=search.value.trim().toLowerCase(),items=models.filter(id=>id.toLowerCase().includes(query));list.innerHTML=items.map(id=>`<button type="button" data-model-id="${esc(id)}" aria-pressed="${id===p.prefs['ai.model']}" ${busy()?'disabled':''}>${providerIcon(provider.value)}<span>${esc(id)}</span>${id===p.prefs['ai.model']?icon('check'):''}</button>`).join('')||'<p>No matching models.</p>';};
  const load=async(force=false)=>{
    const id=provider.value,run=++epoch;status.textContent=busy()?'Finish or stop the current response before changing models.':'Loading the provider catalog…';provider.disabled=!!busy();
    if(busy()){list.replaceChildren();return;}
    const saved=cache.get(id);if(saved&&!force){status.textContent=saved.note||'Provider catalog';render(saved.models);return;}
    list.replaceChildren();panel.setAttribute('aria-busy','true');
    try{const data=await p.api('/ai/models',{provider:id,consent:true});if(run!==epoch||panel.hidden||provider.value!==id)return;const models=[...new Set((data.models||[]).filter(x=>typeof x==='string'&&x.length<240))];cache.set(id,{...data,models});status.textContent=data.note||'Choose a model';render(models);}catch(e){if(run===epoch&&!panel.hidden){status.textContent=e.message;list.innerHTML='<p>Connect this provider with Manage account, then refresh.</p>';}}finally{if(run===epoch)panel.removeAttribute('aria-busy');}
  };
  const open=button=>{if(!panel.hidden&&!closing){close();return;}const continuation=closing?getComputedStyle(panel):null,from={opacity:continuation?.opacity||0,scale:continuation?.scale&&continuation.scale!=='none'?continuation.scale:'.985'};closing=false;anchor=button;provider.value=p.prefs['ai.provider'];search.value='';panel.hidden=false;panel.inert=false;panel.removeAttribute('aria-hidden');p.host.motion.play(panel,[from,{opacity:1,scale:'1'}],220);panel.removeAttribute('aria-busy');for(const b of [title,destination])b.setAttribute('aria-expanded','true');document.dispatchEvent(new Event('lumen:controls'));search.focus();load();};
  for(const button of [title,destination]){button.setAttribute('aria-controls',panel.id);button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-expanded','false');button.onclick=()=>open(button);}
  title.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(title);}};
  provider.onchange=()=>{search.value='';load();};search.oninput=()=>render(cache.get(provider.value)?.models||[]);
  panel.addEventListener('keydown',e=>{const buttons=[...list.querySelectorAll('[data-model-id]:not(:disabled)')],index=buttons.indexOf(document.activeElement);if(e.key==='ArrowDown'&&(document.activeElement===search||index>=0)){e.preventDefault();buttons[(index+1)%buttons.length]?.focus();}else if(e.key==='ArrowUp'&&index>=0){e.preventDefault();buttons[(index-1+buttons.length)%buttons.length]?.focus();}});
  panel.querySelector('[data-model-refresh]').onclick=()=>load(true);panel.querySelector('[data-model-close]').onclick=()=>{close();anchor.focus();};
  panel.querySelector('[data-model-account]').onclick=()=>p.safe(async()=>{const id=provider.value;close();if(id!==p.prefs['ai.provider'])await p.savePreferences({'ai.provider':id,'ai.model':''});await p.settings('ai');});
  list.onclick=e=>{const button=e.target.closest('[data-model-id]');if(!button||busy())return;p.safe(async()=>{button.disabled=true;const id=provider.value,model=button.dataset.modelId,changed=id!==p.prefs['ai.provider'];await p.savePreferences({'ai.provider':id,'ai.model':model});if(changed)p.conversation=crypto.randomUUID?.()||String(Date.now());close();document.getElementById('ai-input').focus();});};
  const outside=e=>{if(e.target.closest('#lumen-options'))return;if(!panel.hidden&&!panel.contains(e.target)&&!title.contains(e.target)&&!destination.contains(e.target))close();};
  const key=e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();e.stopImmediatePropagation();close();anchor.focus();}};
  document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key,true);
  p.openModelPicker=()=>{if(panel.hidden||closing)open(destination);};
  return {close,dispose(){close();delete p.openModelPicker;panel.remove();document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key,true);}};
}
