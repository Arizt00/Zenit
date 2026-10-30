import {icon,escapeHTML as esc} from './icons.js';

const STEPS=[['layers','Elegir','Choose'],['sliders','Configurar','Configure'],['shield','Revisar','Review'],['play','Ejecutar','Execute'],['check','Resultado','Result']];

/** Shared presentation for a real operation. Review never starts work on its own. */
export class TaskFlow{
 constructor(root,{t=(es)=>es,before=null,reviewHost=null,configure=null}={}){
  this.root=root;this.t=t;this.configure=configure;this.stage=0;this.busy=false;this.version=0;
  this.node=document.createElement('section');this.node.className='task-flow';
  this.node.innerHTML=`<ol class="task-flow-steps" aria-label="${esc(t('Pasos de la tarea','Task steps'))}">${STEPS.map(([glyph,es,en],i)=>`<li data-flow-step="${i}"><span>${icon(glyph)}</span><strong>${esc(t(es,en))}</strong></li>`).join('')}</ol>`;
  if(before)before.before(this.node);else root.prepend(this.node);
  this.card=document.createElement('section');this.card.className='task-flow-card';this.card.hidden=true;(reviewHost||this.node).append(this.card);
  this.onInput=e=>{if(e.target.matches('input:not([type=search]),select,textarea')&&!this.card.contains(e.target))this.invalidate();};
  root.addEventListener('input',this.onInput);root.addEventListener('change',this.onInput);this.setStage(0);
 }
 setStage(stage,state=''){
  this.stage=stage;this.node.dataset.state=state;this.card.dataset.state=state;this.card.setAttribute('aria-busy',String(this.busy));
  const caption=this.card.querySelector('.task-flow-title small');if(caption)caption.textContent=stage===4?this.t('Resultado de la tarea','Task result'):stage===3?this.t('Tarea en curso','Task in progress'):this.t('Revisión de la tarea','Task review');
  this.node.querySelectorAll('[data-flow-step]').forEach((n,i)=>{n.dataset.state=i<stage?'complete':i===stage?'current':'next';if(i===stage)n.setAttribute('aria-current','step');else n.removeAttribute('aria-current');});
 }
 choose(label){if(this.busy)return;this.task=label;this.invalidate();}
 invalidate(){if(this.busy)return;this.version++;this.pending=null;this.card.hidden=true;this.card.replaceChildren();this.setStage(1);}
 review(spec){
  if(this.busy)return false;this.pending=spec;this.card.hidden=false;this.setStage(2);const t=this.t;
  this.card.innerHTML=`<header class="task-flow-title">${icon(spec.glyph||'shield')}<div><small>${esc(t('Revisión de la tarea','Task review'))}</small><h4>${esc(spec.title)}</h4></div></header>${spec.summary?`<p>${esc(spec.summary)}</p>`:''}<dl class="task-flow-facts">${(spec.facts||[]).filter(([,value])=>value!==undefined&&value!==null&&value!=='').map(([name,value])=>`<div><dt>${esc(name)}</dt><dd>${esc(String(value))}</dd></div>`).join('')}</dl>${spec.commands?.length?`<pre class="task-flow-command">${esc(spec.commands.join('\n'))}</pre>`:''}<div data-flow-preview></div><div class="task-flow-feedback" role="status" aria-live="polite"></div><div class="task-flow-actions"><button type="button" class="secondary-button" data-flow-edit>${icon('sliders')}${esc(t('Volver a configurar','Back to configuration'))}</button><button type="button" class="primary-button" data-flow-run>${icon('play')}${esc(spec.label||t('Ejecutar tarea','Execute task'))}</button></div>`;
  if(spec.preview)this.card.querySelector('[data-flow-preview]').append(spec.preview);
  this.card.querySelector('[data-flow-edit]').onclick=()=>{this.invalidate();this.configure?.();};
  this.card.querySelector('[data-flow-run]').onclick=()=>this.execute();
  // Keep configuration in place, but bring the explicit review into view.
  this.card.scrollIntoView({block:'nearest',behavior:'auto'});this.card.querySelector('[data-flow-run]').focus({preventScroll:true});return true;
 }
 async execute(){
  if(this.busy||!this.pending)return;const spec=this.pending;this.busy=true;this.setStage(3);this.card.querySelectorAll('button').forEach(b=>b.disabled=true);this.feedback(this.t('Tarea en curso…','Task in progress…'));
  try{
   const result=await spec.run();
   if(result===false){this.busy=false;this.invalidate();return;}
   if(result?.pending){if(this.busy)this.feedback(result.message||this.t('En curso. Consulta la salida en directo.','In progress. View live output.'));return;}
   if(!this.busy)return;
   this.finish(true,result?.message||spec.success||this.t('Tarea completada.','Task completed.'),result?.actions);
  }catch(error){this.finish(false,error.message||String(error));}
 }
 feedback(message){const n=this.card.querySelector('.task-flow-feedback');if(n)n.textContent=message;}
 finish(ok,message,resultActions=[]){
  this.busy=false;this.pending=null;this.setStage(4,ok?'success':'error');this.feedback(message);
  const glyph=this.card.querySelector('.task-flow-title>svg');if(glyph)glyph.outerHTML=icon(ok?'check':'warning');
  const actions=this.card.querySelector('.task-flow-actions');if(actions){actions.innerHTML=`<button type="button" class="secondary-button" data-flow-again>${icon('sliders')}${esc(this.t('Configurar otra tarea','Configure another task'))}</button>`;actions.firstElementChild.onclick=()=>{this.invalidate();this.configure?.();};}
  for(const action of resultActions){const button=document.createElement('button');button.type='button';button.className='secondary-button';button.innerHTML=icon('arrow-right')+esc(action.label);button.onclick=async()=>{try{await action.run();}catch(error){this.feedback(error.message);}};actions?.append(button);}
 }
 track(task){
  if(!this.busy||!task)return;if(!task.done){this.setStage(3);return;}
  this.finish(task.code===0,this.t(task.code===0?'Tarea completada. La salida del proceso está disponible abajo.':'La tarea terminó con errores. Consulta la salida del proceso.',task.code===0?'Task completed. Process output is available below.':'The task finished with errors. View process output.'));
 }
 dispose(){this.root.removeEventListener('input',this.onInput);this.root.removeEventListener('change',this.onInput);this.node.remove();this.card.remove();}
}

export function taskChoices(host,choices,selected,onSelect,t=(es)=>es){
 const nav=document.createElement('div');nav.className='task-flow-choices';nav.setAttribute('role','group');nav.setAttribute('aria-label',t('Qué quieres hacer','What do you want to do'));
 nav.innerHTML=choices.map(([id,glyph,label])=>`<button type="button" class="secondary-button" data-task-choice="${esc(id)}">${icon(glyph)}<span>${esc(label)}</span></button>`).join('');host.append(nav);
 const select=id=>{if(onSelect(id)===false)return;nav.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.taskChoice===id)));};
 nav.onclick=e=>{const b=e.target.closest('[data-task-choice]');if(b)select(b.dataset.taskChoice);};select(selected);return nav;
}
