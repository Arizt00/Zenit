import {icon,escapeHTML as esc} from './icons.js';
const TYPE='application/x-zenit-tab';

/** Virtual folders contain references to live models, never copies of files. */
export class TemporaryTabGroups{
 constructor(h){
  this.h=h;this.ed=h.editor;this.tabs=document.querySelector('#file-tabs');this.bar=document.createElement('div');this.bar.className='temporary-tab-groups';this.bar.setAttribute('aria-label','Carpetas temporales de pestañas');this.tabs.before(this.bar);
  this.ed.tabGroups=[];this.ed.activeTabGroup=null;
  const activate=this.ed.activate.bind(this.ed);this.ed.activate=(path,...args)=>{this.ed.activeTabGroup=this.ed.tabGroups.find(g=>g.paths.includes(path))?.id||null;return activate(path,...args);};
  this.tabs.addEventListener('dragstart',e=>{const tab=e.target.closest('[data-tab]');if(tab){this.source=tab.dataset.tab;e.dataTransfer.setData(TYPE,this.source);}},true);
  this.tabs.addEventListener('dragover',e=>{const tab=e.target.closest('[data-tab]');if(!this.source||!tab||this.source===tab.dataset.tab)return;const r=tab.getBoundingClientRect(),x=(e.clientX-r.left)/r.width;if(x>.22&&x<.78){e.preventDefault();e.stopImmediatePropagation();this.indicate(tab);}},true);
  this.tabs.addEventListener('drop',e=>{
   const tab=e.target.closest('[data-tab]');if(!this.source||!tab||this.source===tab.dataset.tab)return;
   const r=tab.getBoundingClientRect(),x=(e.clientX-r.left)/r.width;if(x<=.22||x>=.78)return;
   e.preventDefault();e.stopImmediatePropagation();this.group(this.source,tab.dataset.tab);this.source=null;this.indicate();
  },true);
  this.bar.addEventListener('dragover',e=>{if(e.target.closest('[data-temporary-group]')&&this.source){e.preventDefault();e.stopPropagation();}});
  this.bar.addEventListener('drop',e=>{const chip=e.target.closest('[data-temporary-group]');if(!chip||!this.source)return;e.preventDefault();e.stopPropagation();const group=this.ed.tabGroups.find(g=>g.id===chip.dataset.temporaryGroup);if(group?.paths[0]&&group.paths[0]!==this.source)this.group(this.source,group.paths[0]);this.source=null;});
  document.addEventListener('dragend',()=>{this.source=null;this.indicate();});
  this.bar.addEventListener('click',e=>{
   const more=e.target.closest('[data-group-more]');if(more){h.showMenu(more,this.ed.tabGroups.map(group=>({label:group.name+' · '+group.paths.length,icon:'folder',run:()=>{this.ed.activeTabGroup=group.id;h.activateFile(group.paths[0]);this.changed();}})),'Carpetas temporales');return;}
   if(e.target.closest('[data-group-back]')){this.ed.activeTabGroup=null;this.changed();this.tabs.querySelector('.active:not([hidden])')?.focus();return;}
   if(e.target.closest('[data-group-undo]')){this.ed.tabGroups=this.ed.tabGroups.filter(g=>g.id!==this.ed.activeTabGroup);this.ed.activeTabGroup=null;this.changed();this.tabs.querySelector('.active:not([hidden])')?.focus();return;}
   const button=e.target.closest('[data-temporary-group]');if(button){this.ed.activeTabGroup=button.dataset.temporaryGroup;const group=this.ed.tabGroups.find(g=>g.id===this.ed.activeTabGroup);if(!group.paths.includes(this.ed.current))h.activateFile(group.paths[0]);this.changed();}
  });
  this.bar.addEventListener('keydown',e=>{if(e.key==='Escape'&&this.ed.activeTabGroup){e.preventDefault();e.stopPropagation();this.ed.activeTabGroup=null;this.changed();this.tabs.querySelector('.active:not([hidden])')?.focus();return;}if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){const buttons=[...this.bar.querySelectorAll('button')],index=buttons.indexOf(e.target);if(index<0)return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?buttons.length-1:(index+(e.key==='ArrowLeft'?-1:1)+buttons.length)%buttons.length;buttons[next]?.focus();}});
  this.bar.addEventListener('dblclick',e=>{const button=e.target.closest('[data-temporary-group]');if(button)this.rename(button.dataset.temporaryGroup);});
  document.addEventListener('zenit:files-renamed',e=>{for(const group of this.ed.tabGroups)group.paths=group.paths.map(path=>{const row=e.detail.find(r=>path===r.oldPath||path.startsWith(r.oldPath+'/'));return row?row.path+path.slice(row.oldPath.length):path;});this.changed();});
  document.addEventListener('zenit:tab-groups-restored',()=>this.render());
  const reset=this.ed.reset.bind(this.ed);this.ed.reset=()=>{this.ed.tabGroups=[];this.ed.activeTabGroup=null;reset();this.render();};this.render();
 }
 indicate(tab){this.tabs.querySelectorAll('.tab-group-target').forEach(t=>t.classList.remove('tab-group-target'));tab?.classList.add('tab-group-target');}
 group(source,target){
  if(!this.ed.models.has(source)||!this.ed.models.has(target))return;
  let group=this.ed.tabGroups.find(g=>g.paths.includes(target));
  for(const g of this.ed.tabGroups)g.paths=g.paths.filter(path=>path!==source);
  if(!group){group={id:crypto.randomUUID(),name:'Carpeta temporal '+(this.ed.tabGroups.length+1),paths:[target]};this.ed.tabGroups.push(group);}
  if(!group.paths.includes(source))group.paths.push(source);this.ed.activeTabGroup=group.id;this.h.activateFile(target);this.changed();
 }
 changed(){this.render();document.dispatchEvent(new Event('zenit:tab-groups-changed'));}
 render(){
  if(!this.ed.tabGroups)return;
  for(const group of this.ed.tabGroups)group.paths=group.paths.filter(path=>this.ed.models.has(path));
  this.ed.tabGroups=this.ed.tabGroups.filter(g=>g.paths.length);
  let current=this.ed.tabGroups.find(g=>g.id===this.ed.activeTabGroup);
  if(current&&!current.paths.includes(this.ed.current)){current=this.ed.tabGroups.find(g=>g.paths.includes(this.ed.current));this.ed.activeTabGroup=current?.id||null;}
  if(!current)this.ed.activeTabGroup=null;
  this.bar.hidden=!this.ed.tabGroups.length;
  const visible=current?[current]:this.ed.tabGroups.slice(0,2);
  this.bar.innerHTML=(current?`<button class="temporary-group-back" data-group-back aria-label="Ver todas las pestañas" title="Ver todas las pestañas · Esc desde el grupo">${icon('chevron-left')}</button>`:'')+visible.map(g=>{const dirty=g.paths.filter(path=>this.ed.isDirty(path)).length;return `<button class="temporary-tab-folder${g===current?' active':''}" data-temporary-group="${esc(g.id)}" title="${esc(g.name)} · carpeta temporal · ${g.paths.length} archivos${dirty?' · '+dirty+' sin guardar':''} · doble clic para cambiar el nombre" aria-label="${esc(g.name)} · carpeta temporal · ${g.paths.length} archivos${dirty?' · '+dirty+' sin guardar':''}" aria-pressed="${g===current}">${icon('folder')}<span>${esc(g.name)}</span><small>${g.paths.length}${dirty?' · ●':''}</small></button>`;}).join('')+(this.ed.tabGroups.length>visible.length?`<button data-group-more aria-label="Más carpetas temporales" title="Más carpetas temporales">${icon('chevron-down')}<small>${this.ed.tabGroups.length}</small></button>`:'')+(current?`<button class="temporary-group-undo" data-group-undo aria-label="Deshacer carpeta temporal" title="Deshacer carpeta temporal y recuperar sus pestañas">${icon('undo')}</button>`:'');
  const members=new Set(this.ed.tabGroups.flatMap(g=>g.paths));
  for(const tab of this.tabs.querySelectorAll('[data-tab]'))tab.hidden=current?!current.paths.includes(tab.dataset.tab):false;
  this.tabs.classList.toggle('temporary-group-open',!!current);
 }
 rename(id){const group=this.ed.tabGroups.find(g=>g.id===id);if(!group)return;this.h.modal('Nombre de carpeta temporal',`<form id="temporary-group-name"><label>Nombre<input name="name" maxlength="60" required value="${esc(group.name)}"></label><div class="modal-actions"><button class="primary-button">Guardar nombre</button></div></form>`);document.querySelector('#temporary-group-name').onsubmit=e=>{e.preventDefault();group.name=new FormData(e.target).get('name').trim()||group.name;this.h.closeModal();this.changed();};}
}
