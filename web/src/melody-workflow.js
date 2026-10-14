import {icon,escapeHTML as esc} from './icons.js';
import {melodyContext} from './melody-context.js';
/** Inspect current scope and retain prompt drafts in this window, separated by workspace. */
export function installMelodyWorkflow(p,input){
  const t=(es,en)=>p.t(es,en),ed=p.host.editor,drafts=new Map();
  const drawer=document.createElement('details');drawer.className='melody-workflow';
  drawer.innerHTML=`<summary>${icon('files')}<span></span><small></small></summary><div class="melody-workflow-body"><div class="melody-context-summary"><strong></strong><small></small></div><pre tabindex="0" aria-label="Composer code context"></pre><div class="melody-workflow-actions"><button type="button" data-context-copy>${icon('copy')}<span></span></button><button type="button" data-draft-save>${icon('plus')}<span></span></button></div><div class="melody-drafts"></div><small class="melody-drafts-note"></small></div>`;
  document.querySelector('.melody-compose-modes').before(drawer);
  const workspace=()=>p.host.workspace(),items=()=>drafts.get(workspace())||[];
  const context=()=>melodyContext({file:ed.getValue(),selection:ed.getSelection(),scope:p.prefs['ai.context'],editing:p.melodyMode==='edit'});
  const refresh=()=>{
    drawer.querySelector('summary>span').textContent=t('Contexto y borradores','Context & drafts');drawer.querySelector('summary>small').textContent=String(items().length);
    if(!drawer.open)return;
    const c=context(),path=ed.current||t('Sin archivo','No file'),binary=ed.models.get(ed.current)?.kind==='binary';
    drawer.querySelector('.melody-context-summary strong').textContent=path.split(/[\\/]/).at(-1);
    drawer.querySelector('.melody-context-summary small').textContent=t('Ámbito: ','Scope: ')+c.kind+' · '+c.content.length+' '+t('caracteres','characters')+(ed.isDirty?.(ed.current)?' · '+t('Sin guardar','Unsaved'):'');
    drawer.querySelector('pre').textContent=binary?t('Los binarios no se incluyen como código.','Binary data is not included as code.'):c.content?c.content.slice(0,6000)+(c.content.length>6000?'\n… '+t('Vista previa limitada','Preview truncated'):''):t('No se adjuntará código con este ámbito.','No code is attached with this scope.');
    drawer.querySelector('[data-context-copy] span').textContent=t('Copiar contexto','Copy context');drawer.querySelector('[data-draft-save] span').textContent=t('Guardar borrador','Save draft');
    drawer.querySelector('[data-draft-save]').disabled=!input.value.trim();
    drawer.querySelector('.melody-drafts').innerHTML=items().map((draft,index)=>`<div><button type="button" data-draft-load="${index}" title="${esc(draft.text.slice(0,240))}">${icon('chat')}<span>${esc(draft.text.slice(0,64))}</span></button><button type="button" class="icon-button" data-draft-remove="${index}" aria-label="${t('Quitar borrador','Remove draft')}">${icon('close')}</button></div>`).join('');
    drawer.querySelector('.melody-drafts-note').textContent=t('Hasta 6 borradores de consulta por proyecto, durante esta ventana. Se restauran en modo Chat.','Up to 6 prompt drafts per project in this window. Restored in Chat mode.');
  };
  drawer.ontoggle=refresh;
  drawer.querySelector('[data-context-copy]').onclick=()=>p.safe(async()=>{const c=context();await navigator.clipboard.writeText(JSON.stringify({path:ed.current||'',scope:c.kind,content:c.content},null,2));p.host.notify(t('Contexto copiado.','Context copied.'));});
  drawer.querySelector('[data-draft-save]').onclick=()=>{const text=input.value.trim();if(!text)return;if(text.length>8000){p.host.notify(t('El borrador admite hasta 8000 caracteres.','A draft supports up to 8000 characters.'),'error');return;}drafts.set(workspace(),[{text},...items().filter(x=>x.text!==text)].slice(0,6));refresh();};
  drawer.onclick=e=>{const load=e.target.closest('[data-draft-load]'),remove=e.target.closest('[data-draft-remove]');if(load){if(p.aiJob||p.aiStarting)return;p.setMelodyMode?.('chat');input.value=items()[+load.dataset.draftLoad].text;input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();}if(remove){drafts.set(workspace(),items().filter((_,index)=>index!==+remove.dataset.draftRemove));refresh();}};
  input.addEventListener('input',refresh);refresh();
  return {refresh,dispose(){input.removeEventListener('input',refresh);drawer.remove();drafts.clear();}};
}
