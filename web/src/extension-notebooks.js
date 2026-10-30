import {icon,escapeHTML as esc} from './icons.js';

/** Notebook cells and kernel output stay outside the source editor surface. */
export class ExtensionNotebooks {
 constructor(host){this.host=host;this.queue=Promise.resolve();this.dismissed=new Map();}
 update(state){
  if(state.disposed){if(this.state?.uri===state.uri)this.root?.remove();return;}
  if(this.dismissed.get(state.uri)===state.reveal)return;
  if(this.state?.uri!==state.uri){this.root?.remove();this.root=document.createElement('section');this.root.className='extension-notebook';this.root.setAttribute('role','region');this.root.setAttribute('aria-label','Cuaderno');document.getElementById('editor-panel').append(this.root);}
  this.state=state;const selected=document.activeElement?.closest('[data-notebook-cell]'),cursor=selected?.selectionStart,pending=selected?.value;
  const root=this.root;root.innerHTML=`<header><span>${icon('file')}<strong>${esc(decodeURIComponent(state.uri.split('/').at(-1)))}${state.dirty?' ·':''}</strong></span><div><select aria-label="Kernel del cuaderno"><option value="">Seleccionar kernel</option>${state.controllers.map(c=>`<option value="${esc(c.id)}" ${state.selected===c.id?'selected':''}>${esc(c.label)}</option>`).join('')}</select><button class="secondary-button" data-notebook-run>${icon('play')}Ejecutar celdas</button><button class="icon-button" data-notebook-interrupt aria-label="Reiniciar kernel">${icon('stop')}</button><button class="icon-button" data-notebook-save aria-label="Guardar cuaderno">${icon('save')}</button><button class="icon-button" data-notebook-close aria-label="Cerrar cuaderno">${icon('close')}</button></div></header>${state.controllers.length?'':'<p class="platform-notice">No hay un kernel preparado. Configura un intérprete y el kernel de Jupyter para ejecutar las celdas.</p>'}<div class="extension-notebook-cells">${state.cells.map((c,i)=>`<article><div><span>${esc(c.kind===1?'Markdown':c.language)} ${c.executionSummary?.executionOrder??''}</span>${c.kind===2?`<button class="icon-button" data-notebook-run-cell="${i}" aria-label="Ejecutar celda ${i+1}">${icon('play')}</button>`:''}</div><textarea data-notebook-cell="${i}" aria-label="Celda ${i+1}" spellcheck="false" rows="${Math.max(2,Math.min(22,c.text.split('\n').length+1))}">${esc(c.text)}</textarea>${c.outputs.flatMap(o=>o.items).map(item=>{let text;try{text=new TextDecoder().decode(Uint8Array.from(atob(item.data),c=>c.charCodeAt(0)));}catch{text='No se puede decodificar la salida.';}return `<pre aria-label="Salida de la celda">${esc(/^(?:text\/|application\/vnd\.code\.notebook\.|application\/json)/.test(item.mime)?text:'Salida '+item.mime+' · '+item.data.length+' bytes codificados')}</pre>`;}).join('')}</article>`).join('')}</div>`;
  root.querySelector('select').onchange=e=>this.control('select',{controller:e.target.value});
  root.querySelector('[data-notebook-close]').onclick=()=>{this.dismissed.set(state.uri,state.reveal);root.remove();this.root=null;this.state=null;};
  root.querySelector('[data-notebook-interrupt]').onclick=()=>this.control('interrupt');
  root.querySelector('[data-notebook-save]').onclick=()=>this.control('save');root.querySelector('[data-notebook-run]').onclick=()=>this.control('execute');
  root.querySelectorAll('[data-notebook-run-cell]').forEach(b=>b.onclick=()=>this.control('execute',{index:Number(b.dataset.notebookRunCell)}));
  root.querySelectorAll('[data-notebook-cell]').forEach(input=>input.onchange=()=>this.control('edit',{index:Number(input.dataset.notebookCell),text:input.value}));
  if(selected){const next=root.querySelector(`[data-notebook-cell="${selected.dataset.notebookCell}"]`);if(next)next.value=pending;next?.focus();next?.setSelectionRange(cursor,cursor);}
 }
 control(action,extra={}){const state=this.state;this.queue=this.queue.catch(()=>{}).then(()=>this.host.platform.api('/extensions/runtime/request',{id:state.ownerExtension,method:'notebook',uri:state.uri,action,...extra})).catch(e=>this.host.notify(e.message,'error'));return this.queue;}
}
