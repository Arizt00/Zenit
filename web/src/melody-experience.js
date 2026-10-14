import {icon} from './icons.js';
import {melodyContext} from './melody-context.js';
import {installMelodyResearch} from './melody-research.js';
import {installModelPicker} from './melody-model-picker.js';
import {providerIcon,providerName} from './provider-identity.js';

/** A visible context, destination, and stop action throughout a conversation. */
export function installMelodyExperience(host){
  const p=host.platform,ed=p.host.editor,t=(es,en)=>p.t(es,en),body=document.getElementById('assistant-body');
  const status=document.createElement('div');status.className='melody-session-strip';
  status.innerHTML=`<button class="melody-destination" type="button"><i class="melody-provider-icon"></i><span></span>${icon('chevron-down')}</button><button type="button" class="icon-button melody-new-chat" data-action="new-chat">${icon('plus')}</button>`;
  document.querySelector('.melody-tagline').after(status);
  const cancel=document.getElementById('ai-cancel-generation');status.append(cancel);
  cancel.title='Stop response';cancel.setAttribute('aria-label','Stop response');
  const modelPicker=installModelPicker(p,status.querySelector('.melody-destination'));
  const composer=document.querySelector('.ai-composer'),input=document.getElementById('ai-input');
  const modes=document.createElement('div');modes.className='melody-compose-modes';modes.setAttribute('role','group');modes.setAttribute('aria-label','Message mode');
  modes.innerHTML=`<button type="button" data-melody-mode="chat" aria-pressed="true">${icon('sparkles')}<span>Chat</span></button><button type="button" data-melody-mode="edit" aria-pressed="false">${icon('code')}<span>Edit file</span></button><small class="melody-mode-hint"></small>`;
  composer.before(modes);p.melodyMode='chat';
  const context=document.querySelector('.composer-context>button');
  const tasks=document.createElement('div');tasks.className='melody-context-actions';
  tasks.innerHTML=`<button type="button" data-melody-task="diagnostics">${icon('bug')}<span>Review diagnostics</span></button><button type="button" data-melody-task="tests">${icon('flask')}<span>Plan tests</span></button>`;
  modes.before(tasks);installMelodyResearch(host);
  tasks.onclick=e=>{const b=e.target.closest('[data-melody-task]');if(!b||b.disabled)return;p.safe(async()=>{
    if(!ed.current)throw Error(t('Abre un archivo primero.','Open a file first.'));
    const items=p.diagnosticMap.get(ed.current)||[];
    const question=b.dataset.melodyTask==='tests'?'Propose a focused test plan for the supplied code. Cover behavior, edge cases and realistic failure cases. Explain how to run the tests; do not change any files.':'Review these current editor diagnostics. Prioritize the failures, explain the cause and propose a reviewable fix. Do not edit files.\n'+JSON.stringify({path:ed.current,diagnostics:items},null,2);
    input.value=question;await p.sendAI(question,{consult:true});
  });};
  context.onclick=e=>{e.stopPropagation();host.showMenu(context,[
    {label:t('Selección o archivo','Selection or file'),icon:'code',run:()=>p.savePreference('ai.context','selection')},
    {label:t('Archivo completo','Whole file'),icon:'file',run:()=>p.savePreference('ai.context','file')},
    {label:t('Sin código','No code'),icon:'chat',run:()=>p.savePreference('ai.context','none')}
  ],t('Contexto de Melody','Melody context'));};
  const refresh=()=>{
    const busy=!!p.aiJob||p.aiStarting,editing=p.melodyMode==='edit';
    const c=melodyContext({file:ed.getValue(),selection:ed.getSelection(),scope:p.prefs['ai.context'],editing});
    const path=(ed.current||'').replaceAll('\\','/').split('/').pop();
    const text=c.kind==='none'?t('Sin código','No code'):c.kind==='selection'?t('Selección','Selection')+' · '+c.content.length+' '+t('caracteres','chars'):path||t('Sin archivo','No file');
    context.querySelector('span').textContent=text;context.title=(ed.current||'')+' · '+c.kind;context.dataset.scope=c.kind;
    const destination=status.querySelector('.melody-destination'),provider=p.prefs['ai.provider'];
    const glyph=status.querySelector('.melody-provider-icon');if(glyph.dataset.provider!==provider){glyph.dataset.provider=provider;glyph.innerHTML=providerIcon(provider);}
    destination.querySelector(':scope>span').textContent=p.prefs['ai.model']?providerName(provider)+' · '+p.prefs['ai.model']:t('Conectar un modelo','Connect a model');
    destination.dataset.connected=String(p.connectionStates?.get(provider)?.authenticated===true);
    destination.title=t('Proveedor, cuenta y modelo','Provider, account and model');
    status.querySelector('.melody-new-chat').title=t('Nueva conversación','New conversation');status.querySelector('.melody-new-chat').setAttribute('aria-label',t('Nueva conversación','New conversation'));
    modes.querySelectorAll('button').forEach(b=>{b.disabled=busy;b.setAttribute('aria-pressed',String(b.dataset.melodyMode===p.melodyMode));});
    modes.querySelector('[data-melody-mode=edit]>span').textContent=t('Editar archivo','Edit file');
    modes.querySelector('small').textContent=busy?t('Generando…','Working…'):editing?t('Cambios en vivo · deshacer disponible','Live changes · undo available'):t('Preguntas y acciones','Questions & actions');
    input.placeholder=editing?t('Describe cómo cambiar este archivo…','Describe how to change this file…'):t('Pregunta o describe lo que quieres construir…','Ask a question or describe what to build…');
    body.dataset.melodyBusy=String(busy);
    tasks.querySelectorAll('button').forEach(b=>b.disabled=busy);
    tasks.querySelector('[data-melody-task=diagnostics] span').textContent=t('Revisar diagnósticos','Review diagnostics');tasks.querySelector('[data-melody-task=tests] span').textContent=t('Plan de pruebas','Plan tests');
    document.getElementById('ai-edit-file').title=t('Editar archivo en vivo','Edit file live');
  };
  modes.onclick=e=>{const button=e.target.closest('[data-melody-mode]');if(!button||button.disabled)return;p.melodyMode=button.dataset.melodyMode;refresh();input.focus();};
  document.addEventListener('zenit:provider-state',refresh);
  const send=p.sendAI.bind(p);p.sendAI=async(question,options={})=>{try{const promise=send(question,{...options,edit:options.edit===true||p.melodyMode==='edit'});refresh();return await promise;}finally{refresh();}};
  const clear=p.clearAI.bind(p);p.clearAI=async(...args)=>{await clear(...args);p.melodyMode='chat';refresh();};
  const apply=p.applyPreferences.bind(p);p.applyPreferences=(...args)=>{const result=apply(...args);refresh();return result;};
  const active=ed.callbacks.active;ed.callbacks.active=(...args)=>{active?.(...args);refresh();};
  const change=ed.callbacks.change;ed.callbacks.change=(...args)=>{change?.(...args);refresh();};
  const selection=ed.view?.onDidChangeCursorSelection?.(refresh);
  const observer=new MutationObserver(refresh);observer.observe(document.querySelector('.provider-status-dot'),{attributes:true,attributeFilter:['class']});
  const hero=document.getElementById('assistant-hero');
  const kicker=document.createElement('span');kicker.className='melody-hero-kicker';kicker.textContent=t('TU COMPAÑERA DE CÓDIGO','YOUR CODING COMPANION');hero.querySelector('.melody-copy').prepend(kicker);
  refresh();return {dispose(){modelPicker.dispose();selection?.dispose();observer.disconnect();document.removeEventListener('zenit:provider-state',refresh);}};
}
