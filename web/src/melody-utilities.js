import {icon} from './icons.js';

/** Secondary tools stay one click away without taking space from the conversation. */
export function installMelodyUtilities(p){
  const t=(es,en)=>p.t(es,en),root=document.getElementById('assistant-panel');
  const button=document.createElement('button');button.type='button';button.className='melody-utilities-toggle';button.innerHTML=icon('sliders');button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','melody-utilities');
  document.querySelector('.melody-compose-modes').append(button);
  const panel=document.createElement('section');panel.id='melody-utilities';panel.className='melody-utilities';panel.hidden=true;panel.setAttribute('role','dialog');
  panel.innerHTML=`<header><strong></strong><button type="button" class="icon-button" data-utilities-close>${icon('close')}</button></header><div class="melody-utility-tabs" role="tablist"><button type="button" role="tab" data-utility-tab="tools"></button><button type="button" role="tab" data-utility-tab="context"></button></div><div class="melody-utility-pane" data-utility-pane="tools" role="tabpanel"></div><div class="melody-utility-pane" data-utility-pane="context" role="tabpanel" hidden></div>`;
  root.append(panel);const tools=panel.querySelector('[data-utility-pane=tools]'),context=panel.querySelector('[data-utility-pane=context]');
  const starters=document.createElement('div');starters.className='melody-utility-starters';tools.append(starters);
  for(const selector of ['[data-ai-action=generate]','#ai-actions [data-view=search]']){const node=document.querySelector(selector);if(node)starters.append(node);}
  tools.append(document.querySelector('.melody-context-actions'),document.querySelector('.melody-research'));
  context.append(document.querySelector('.melody-tools-row'),document.querySelector('.melody-workflow'));
  let epoch=0,closing=false;
  const close=()=>{if(panel.hidden||closing)return;closing=true;const id=++epoch;panel.inert=true;button.setAttribute('aria-expanded','false');const style=getComputedStyle(panel),a=p.host.motion.play(panel,[{opacity:style.opacity,translate:style.translate==='none'?'0 0':style.translate},{opacity:0,translate:'0 4px'}],140);const done=()=>{if(id===epoch){panel.hidden=true;panel.inert=false;closing=false;}};if(a)a.finished.catch(()=>{}).then(done);else done();};
  const tab=name=>{panel.querySelectorAll('[data-utility-tab]').forEach(b=>{const selected=b.dataset.utilityTab===name;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;});panel.querySelectorAll('[data-utility-pane]').forEach(n=>n.hidden=n.dataset.utilityPane!==name);if(name==='context'){const drawer=panel.querySelector('.melody-workflow');drawer.open=true;drawer.dispatchEvent(new Event('toggle'));}};
  button.onclick=()=>{if(!panel.hidden&&!closing){close();return;}++epoch;closing=false;panel.hidden=false;panel.inert=false;button.setAttribute('aria-expanded','true');p.openModelPicker&&document.getElementById('melody-model-picker')?.querySelector('[data-model-close]')?.click();p.host.motion.play(panel,[{opacity:0,translate:'0 5px'},{opacity:1,translate:'0 0'}],190);panel.querySelector('[aria-selected=true]')?.focus();};
  panel.querySelector('[data-utilities-close]').onclick=()=>{close();button.focus();};
  panel.querySelector('.melody-utility-tabs').onclick=e=>{const b=e.target.closest('[data-utility-tab]');if(b)tab(b.dataset.utilityTab);};
  panel.querySelector('.melody-utility-tabs').onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const next=panel.querySelector('[aria-selected=false]');tab(next.dataset.utilityTab);next.focus();}};
  const outside=e=>{if(!panel.hidden&&!panel.contains(e.target)&&!button.contains(e.target))close();};
  tools.addEventListener('click',e=>{if(e.target.closest('[data-ai-action],[data-view],[data-melody-task],[data-research]'))close();});
  const key=e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();e.stopImmediatePropagation();close();button.focus();}};
  document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key,true);
  const refresh=()=>{button.title=t('Herramientas y memoria','Tools and memory');button.setAttribute('aria-label',button.title);panel.setAttribute('aria-label',button.title);panel.querySelector('header strong').textContent='Melody';panel.querySelector('[data-utilities-close]').setAttribute('aria-label',t('Cerrar herramientas','Close tools'));panel.querySelector('[data-utility-tab=tools]').textContent=t('Herramientas','Tools');panel.querySelector('[data-utility-tab=context]').textContent=t('Contexto y memoria','Context and memory');};
  tab('tools');refresh();return {refresh,dispose(){close();document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key,true);panel.remove();button.remove();}};
}
