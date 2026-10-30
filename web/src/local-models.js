import {icon,escapeHTML as esc} from './icons.js';

/** Optional GGUF files share the resumable download manager; never auto-load a model. */
export function mountLocalModels(platform){
  if(platform.prefs['ai.provider']!=='emma')return;
  const parent=document.querySelector('.provider-detail');if(!parent)return;
  const root=document.createElement('section');root.className='local-ai-models';parent.append(root);
  root.innerHTML=`<div class="local-ai-models-heading"><h4>${platform.t('Modelos locales','Local models')}</h4><button class="icon-button" data-local-refresh aria-label="${platform.t('Actualizar modelos locales','Refresh local models')}">${icon('refresh')}</button></div><p class="muted-small">${platform.t('Descarga opcional y verificada. El modelo se carga cuando envías una consulta; tu modelo actual se conserva.','Optional verified download. Models load when you send a question; your current model stays selected.')}</p><div data-local-model-list></div><p data-local-model-status role="status"></p>`;
  const list=root.querySelector('[data-local-model-list]'),status=root.querySelector('[data-local-model-status]');let refreshing=false,timer;
  const refresh=async()=>{
    clearTimeout(timer);
    if(!root.isConnected||refreshing)return;refreshing=true;let pending=false;
    try{
      const data=await platform.api('/ai/local-models');if(!root.isConnected)return;
      list.innerHTML=data.models.map(model=>{
        const download=model.download,state=download?.status||'available',running=['downloading','verifying'].includes(state);pending ||= running;
        const progress=download?Math.min(100,Math.round(100*download.bytes/model.bytes)):0;
        const label=model.ready?platform.t('Verificado · listo para elegir','Verified · ready to choose'):state==='verifying'?platform.t('Verificando SHA-256…','Verifying SHA-256…'):running?platform.t(`Descargando · ${progress} %`,`Downloading · ${progress}%`):state==='paused'?platform.t('Descarga pausada','Download paused'):state==='error'?download.error:platform.t('Disponible para descargar','Available to download');
        return `<article class="local-ai-model" data-local-model="${esc(model.id)}"><div class="local-ai-model-title">${icon('cpu')}<div><strong>${esc(model.name)}</strong><small>${esc(model.quantization)} · ${(model.bytes/1e9).toFixed(2)} GB · ${esc(model.license)}</small></div></div><a href="${esc(model.source)}" target="_blank" rel="noopener noreferrer">${esc(model.repository)}</a><p class="muted-small">${esc(label)}</p>${running?`<progress max="100" value="${progress}" aria-label="${esc(label)}"></progress>`:''}<div class="local-ai-model-actions">${model.ready?`<button class="secondary-button" data-local-use>${icon('check')}${platform.t('Usar en Emma','Use in Emma')}</button>`:running?`<button class="secondary-button" data-local-pause="${esc(download.id)}">${platform.t('Pausar','Pause')}</button>`:`<button class="secondary-button" data-local-download>${icon('download')}${download?platform.t('Reanudar','Resume'):platform.t('Descargar GGUF','Download GGUF')}</button>`}<small>${platform.t('Requiere memoria suficiente y un motor llama.cpp compatible.','Requires sufficient memory and a compatible llama.cpp engine.')}</small></div></article>`;
      }).join('');
    }catch(error){if(root.isConnected)status.textContent=error.message;}
    finally{refreshing=false;if(pending&&root.isConnected)timer=setTimeout(refresh,1000);}
  };
  root.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button||button.disabled)return;
    if(button.hasAttribute('data-local-refresh')){refresh();return;}
    const model=button.closest('[data-local-model]')?.dataset.localModel;if(!model)return;
    platform.safe(async()=>{
      if(platform.aiJob||platform.aiStarting)throw Error(platform.t('Espera o detén la respuesta actual.','Wait for or stop the current response.'));
      button.disabled=true;status.textContent='';
      try{
        if(button.hasAttribute('data-local-use')){
          await platform.api('/ai/local-models/use',{model,consent:true});
          platform.conversation=crypto.randomUUID();await platform.syncPreferences();await platform.renderSettingsContent();return;
        }
        if(button.hasAttribute('data-local-pause'))await platform.api('/downloads/pause',{id:button.dataset.localPause});
        else await platform.api('/ai/local-models/download',{model,consent:true});
        await refresh();
      }catch(error){status.textContent=error.message;throw error;}
      finally{if(button.isConnected)button.disabled=false;}
    });
  });
  refresh();
}
