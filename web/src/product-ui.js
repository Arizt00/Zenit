import {icon} from './icons.js';

/** Keep existing actions and handlers; expose secondary tools through one menu. */
export function installProductUI(host){
  const platform=host.platform;
  if(platform?.sessionbar){
    const picker=document.createElement('button');picker.className='console-mode zenit-terminal-picker';picker.setAttribute('aria-haspopup','menu');picker.setAttribute('aria-label','Seleccionar terminal');picker.innerHTML=icon('terminal')+'<span>Consola</span>'+icon('chevron-down');
    document.querySelector('.terminal-tools').prepend(picker);
    picker.onclick=()=>host.showMenu(picker,[{label:'Consola de tareas',icon:'terminal',run:()=>platform.useConsole()},...Array.from(platform.terminals.values()).map(t=>({label:t.profile?.label||t.id,icon:'terminal',run:()=>platform.selectTerminal(t.id)})),{separator:true},{label:'Nueva terminal',icon:'plus',run:()=>platform.terminalProfiles()},...(platform.showingPTY&&platform.activeTerminal?[{label:'Cerrar esta sesión',icon:'trash',run:()=>platform.closeTerminal(platform.activeTerminal)}]:[])],'Terminales');
    const original=platform.renderActiveTerminal.bind(platform);platform.renderActiveTerminal=(...args)=>{const result=original(...args),terminal=platform.terminals.get(platform.activeTerminal);picker.querySelector('span').textContent=platform.showingPTY?(terminal?.profile?.label||'Terminal'):'Consola';return result;};
    platform.sessionbar.classList.add('zenit-sessions-hidden');document.querySelector('.console-mode:not(.zenit-terminal-picker)')?.classList.add('zenit-overflow-action');
  }
  function compact(container,keep){
    if(!container)return;
    const hidden=[...container.querySelectorAll('button')].filter(button=>!button.matches(keep)&&!button.classList.contains('dock-grip'));
    hidden.forEach(button=>button.classList.add('zenit-overflow-action'));
    const menu=document.createElement('button');menu.type='button';menu.className='icon-button zenit-tools-menu';menu.setAttribute('aria-label','Más acciones');menu.title='Más acciones';menu.innerHTML=icon('more');container.append(menu);
    menu.onclick=()=>host.showMenu(menu,hidden.map(button=>({label:button.getAttribute('aria-label')||button.title||button.textContent.trim(),icon:button.querySelector('[data-glyph]')?.dataset.glyph||'settings',disabled:button.disabled,run:()=>button.click()})),'Acciones');
  }
  compact(document.querySelector('#project-panel .heading-actions'),'[data-action="new-file"],[data-action="project-menu"],[data-collapse-panel],[title*="escritorio"]');
  compact(document.querySelector('#assistant-panel .heading-actions'),'[title*="escritorio"]');
  compact(document.querySelector('.editor-tabbar'),'.file-tab,.new-tab,.file-group');
  const crumbs=document.createElement('span');crumbs.className='breadcrumbs-actions';
  for(const [action,glyph,label] of [['run','play','Ejecutar archivo'],['debug-view','bug','Depurar archivo'],['settings','settings','Ajustes']]){
    const button=document.createElement('button');button.className='icon-button';button.type='button';button.title=label;button.setAttribute('aria-label',label);button.innerHTML=icon(glyph);button.onclick=()=>host.perform(action);crumbs.append(button);
  }
  // Breadcrumbs are updated independently; reuse the same toolbar after each update.
  const updateCrumbs=()=>document.querySelector('#breadcrumbs')?.append(crumbs);document.addEventListener('zenit:breadcrumbs',updateCrumbs);
  document.querySelector('#breadcrumbs')?.append(crumbs);
  const run=document.querySelector('.run-button'),panes=document.querySelector('.pane-switcher');if(run&&panes)run.after(panes);
  const editorMenu=document.querySelector('.editor-tabbar .zenit-tools-menu'),previousMenu=editorMenu?.onclick;if(editorMenu)editorMenu.onclick=()=>host.showMenu(editorMenu,[...Array.from(panes?.querySelectorAll('button')||[]).map(button=>({label:button.title||button.getAttribute('aria-label'),icon:'layout',run:()=>button.click()})),{label:'Más herramientas del editor',icon:'more',run:previousMenu}],'Editor');
  const explorer=document.querySelector('.rail-item[data-view=explorer] [data-icon]');if(explorer)explorer.innerHTML=icon('folder');
  const explain=document.querySelector('[data-ai-action=explain]'),generate=document.querySelector('[data-ai-action=generate]'),refactor=document.querySelector('[data-ai-action=refactor]'),fix=document.querySelector('[data-ai-action=fix]');
  const cards=[[explain,'shield','Explica este código','Te lo detallo paso a paso'],[generate,'build','Genera una función','A partir de una descripción'],[refactor,'search','Busca en tu proyecto','Encuentra archivos, clases, símbolos…'],[fix,'flask','Resuelve un error','Analiza el problema y te da una solución']];
  for(const [button,glyph,title,subtitle] of cards){if(!button)continue;button.querySelector('.action-card-icon').innerHTML=icon(glyph);button.querySelector('strong').textContent=title;button.querySelector('small').textContent=subtitle;document.querySelector('#ai-actions').append(button);}
  if(refactor){refactor.removeAttribute('data-ai-action');refactor.dataset.view='search';}
  const title=document.querySelector('.assistant-heading-title');title.querySelector('h2').hidden=false;title.insertAdjacentHTML('beforeend','<span class="melody-beta">BETA</span>');
  const subtitle=document.createElement('p');subtitle.className='melody-tagline';subtitle.textContent='Tu asistente de desarrollo en Zénit';document.querySelector('.assistant-heading').after(subtitle);
  const provider=document.querySelector('.ai-provider-bar');if(provider)subtitle.after(provider);
  let closeProvider=()=>{};
  if(provider){provider.classList.add('melody-provider-details');const name=title.querySelector('h2');name.setAttribute('tabindex','0');name.setAttribute('role','button');name.setAttribute('aria-label','Proveedor y modelo de Melody');name.setAttribute('aria-expanded','false');closeProvider=()=>{provider.classList.remove('is-open');name.setAttribute('aria-expanded','false');};const toggle=()=>{const open=provider.classList.toggle('is-open');name.setAttribute('aria-expanded',String(open));};name.onclick=toggle;name.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}};}
  const providerPointer=event=>{if(!provider?.contains(event.target)&&!title.contains(event.target))closeProvider();};
  const providerKey=event=>{if(event.key==='Escape'&&provider?.classList.contains('is-open')){event.stopPropagation();closeProvider();title.querySelector('h2').focus();}};
  document.addEventListener('pointerdown',providerPointer);document.addEventListener('keydown',providerKey);
  const input=document.querySelector('#ai-input');input.placeholder='Escribe un mensaje a Melody…';
  const edit=document.getElementById('ai-edit-file');if(edit){edit.classList.add('ai-edit-file');edit.title='Editar archivo con permiso';edit.setAttribute('aria-label','Editar archivo con permiso');edit.innerHTML=icon('code');document.querySelector('.ai-composer').append(edit);}
  document.querySelector('.send-button').innerHTML=icon('arrow-right');
  const context=document.querySelector('.composer-context>button');if(context){context.dataset.action='context-picker';context.innerHTML=icon('context')+'<span>Contexto: archivo actual</span>';context.onclick=event=>{event.stopPropagation();host.showMenu(context,[{label:'Archivo actual',icon:'file',run:()=>host.perform('ai-settings')},{label:'Refactorizar el código',icon:'refactor',run:()=>{input.value='Propón una refactorización de este código.';input.focus();}}],'Contexto y asistencia');};}
  let locale;
  const refresh=()=>{
    const next=platform.prefs['general.locale'];if(locale===next)return;locale=next;
    const t=(es,en)=>platform.t(es,en),set=(selector,text)=>{const node=document.querySelector(selector);if(node)node.textContent=text;};
    const english=[['Explain this code','I’ll walk you through it'],['Generate a function','From a description'],['Search your project','Find files, classes and symbols…'],['Resolve an error','Understand the problem and its solution']];
    cards.forEach(([button,,heading,detail],i)=>{if(button){button.querySelector('strong').textContent=t(heading,english[i][0]);button.querySelector('small').textContent=t(detail,english[i][1]);}});
    subtitle.textContent=t('Tu asistente de desarrollo en Zénit','Your development assistant in Zénit');
    input.placeholder=t('Escribe un mensaje a Melody…','Write a message to Melody…');
    set('.melody-copy h3',t('Hola, soy Melody.','Hello, I’m Melody.'));
    const description=document.querySelector('.melody-copy p');if(description)description.innerHTML=t('Te ayudo a construir, entender y mejorar tu código.<br>¿En qué puedo ayudarte hoy?','I help you build, understand and improve your code.<br>How can I help you today?');
    set('.melody-disclaimer',t('Melody puede cometer errores. Verifica sus respuestas.','Melody can make mistakes. Check its responses.'));
    set('.composer-context>button>span',t('Contexto: archivo actual','Context: current file'));
  };
  const applyPreferences=platform.applyPreferences.bind(platform);platform.applyPreferences=(...args)=>{const result=applyPreferences(...args);refresh();return result;};refresh();
  return {dispose(){document.removeEventListener('zenit:breadcrumbs',updateCrumbs);document.removeEventListener('pointerdown',providerPointer);document.removeEventListener('keydown',providerKey);}};
}
