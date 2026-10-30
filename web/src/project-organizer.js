import {icon,fileIcon,folderIcon,escapeHTML as esc} from './icons.js';
export const FILES_TYPE='application/x-zenit-files';
export const PICKUP_DELAY=700;
const pathOf=row=>row?.dataset.file??row?.dataset.dir;
const parentOf=path=>path.split('/').slice(0,-1).join('/');

/** Selection and order are UI state; moves are reviewed server transactions. */
export class ProjectOrganizerUI{
 constructor(h){
  this.h=h;this.selected=new Set();this.orders={};this.history=[];this.workspace=h.workspace();this.sidebar=document.querySelector('#sidebar-content');this.anchor=null;this.drag=null;this.timer=null;
  this.status=document.createElement('div');this.status.className='explorer-selection-bar';this.status.hidden=true;this.status.setAttribute('role','status');this.sidebar.before(this.status);
  this.destination=document.createElement('div');this.destination.className='explorer-drop-preview';this.destination.hidden=true;this.destination.setAttribute('role','status');document.body.append(this.destination);
  this.status.addEventListener('click',e=>{if(e.target.closest('[data-selection-clear]'))this.clear();if(e.target.closest('[data-selection-melody]'))this.safe(()=>this.melody());if(e.target.closest('[data-selection-move]'))this.moveSelection();if(e.target.closest('[data-selection-undo]'))this.safe(()=>this.undo());});
  this.sidebar.addEventListener('keydown',e=>{if(e.target.matches('input,textarea'))return;if((e.ctrlKey||e.metaKey)&&!e.shiftKey&&e.key.toLowerCase()==='z'&&this.history.length){e.preventDefault();e.stopImmediatePropagation();this.safe(()=>this.undo());}else if(e.altKey&&e.key.toLowerCase()==='m'){e.preventDefault();e.stopImmediatePropagation();this.moveSelection();}else if(['ArrowUp','ArrowDown','Home','End'].includes(e.key)){const rows=this.rows(),index=rows.indexOf(e.target.closest('.tree-row'));if(index<0)return;e.preventDefault();e.stopImmediatePropagation();const next=rows[e.key==='Home'?0:e.key==='End'?rows.length-1:Math.max(0,Math.min(rows.length-1,index+(e.key==='ArrowUp'?-1:1)))];if(e.shiftKey){this.selected.add(pathOf(rows[index]));this.selected.add(pathOf(next));this.paint();}next?.focus();}},true);
  this.sidebar.addEventListener('click',e=>this.click(e),true);
  this.sidebar.addEventListener('keydown',e=>{if(e.key==='Escape'){this.clear();e.stopPropagation();}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'&&!e.target.matches('input')){e.preventDefault();e.stopPropagation();this.rows().forEach(row=>this.selected.add(pathOf(row)));this.paint();}},true);
  this.sidebar.addEventListener('dragstart',e=>this.start(e),true);
  this.sidebar.addEventListener('dragover',e=>this.over(e),true);
  this.sidebar.addEventListener('drop',e=>{if(!this.drag)return;e.preventDefault();e.stopPropagation();const drag=this.drag,where=this.where(e);this.finish(where.row);this.safe(()=>this.drop(drag,where));},true);
  this.sidebar.addEventListener('dragleave',e=>{if(!this.sidebar.contains(e.relatedTarget)){this.cancelHover();this.indicate();}});
  document.addEventListener('dragend',()=>this.finish());
  document.addEventListener('dragover',e=>{if(this.drag)this.moveGhost(e.clientX,e.clientY);},true);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&this.drag)this.finish();},true);
  this.sidebar.addEventListener('contextmenu',e=>{const row=e.target.closest('.tree-row');if(row&&!this.selected.has(pathOf(row))){this.selected=new Set([pathOf(row)]);this.paint();}},true);
  this.sidebar.addEventListener('zenit:tree-rendered',()=>this.paint());
  document.addEventListener('zenit:files-renamed',e=>{const map=path=>{const row=e.detail.find(r=>path===r.oldPath||path.startsWith(r.oldPath+'/'));return row?row.path+path.slice(row.oldPath.length):path;};this.selected=new Set([...this.selected].map(map));this.orders=Object.fromEntries(Object.entries(this.orders).map(([key,values])=>[map(key),values.map(map)]));this.paint();});
  document.addEventListener('zenit:files-deleted',e=>{const keep=path=>!e.detail.some(p=>path===p||path.startsWith(p+'/'));this.selected=new Set([...this.selected].filter(keep));this.orders=Object.fromEntries(Object.entries(this.orders).filter(([key])=>keep(key)).map(([key,values])=>[key,values.filter(keep)]));this.paint();});
  this.load();
 }
 safe(fn){return Promise.resolve().then(fn).catch(error=>this.h.notify(error.message,'error',6500));}
 async load(){this.workspace=this.h.workspace();this.selected.clear();this.history=[];this.orders={};const data=await this.h.api('/platform/files/layout');if(this.workspace===this.h.workspace()){this.orders=data.orders||{};this.h.renderTree();}}
 sort(nodes,parent=''){const order=this.orders[parent]||[],index=new Map(order.map((p,i)=>[p,i]));return [...nodes].sort((a,b)=>(index.get(a.path)??1e9)-(index.get(b.path)??1e9));}
 rows(){return [...this.sidebar.querySelectorAll('.tree-row')].filter(row=>row.getClientRects().length);}
 click(e){
  const row=e.target.closest('.tree-row');if(!row)return;const path=pathOf(row);
  if(e.ctrlKey||e.metaKey||e.shiftKey){
   e.preventDefault();e.stopImmediatePropagation();
   if(e.shiftKey&&this.anchor){const rows=this.rows().map(pathOf),a=rows.indexOf(this.anchor),b=rows.indexOf(path);if(a>=0&&b>=0)rows.slice(Math.min(a,b),Math.max(a,b)+1).forEach(p=>this.selected.add(p));}
   else this.selected.has(path)?this.selected.delete(path):this.selected.add(path);
  }else{this.selected=new Set([path]);this.anchor=path;}
  this.paint();
 }
 clear(){this.selected.clear();this.paint();}
 paint(){
  if(this.workspace!==this.h.workspace()){this.safe(()=>this.load());return;}
  for(const row of this.sidebar.querySelectorAll('.tree-row')){row.draggable=true;row.classList.toggle('multi-selected',this.selected.has(pathOf(row)));row.classList.toggle('is-carried',!!this.drag&&this.drag.paths.includes(pathOf(row)));row.setAttribute('aria-selected',String(this.selected.has(pathOf(row))));}
  const root=this.sidebar.querySelector('.tree-root');if(root){root.dataset.dropRoot='true';root.title='Suelta aquí para sacar archivos a la raíz del proyecto';}
  this.status.hidden=this.drag?this.drag.statusHidden:!this.selected.size&&!this.history.length;
  this.status.innerHTML=`<span>${this.selected.size?`${this.selected.size} ${this.drag?'recogidos':this.selected.size===1?'elemento':'elementos'}`:'Movimiento completado'}</span>${this.history.length?`<button type="button" data-selection-undo title="Deshacer último movimiento u orden · Ctrl+Z en Proyecto" aria-label="Deshacer último movimiento" ${this.busy?'disabled':''}>${icon('undo')}</button>`:''}${this.selected.size?`<button type="button" data-selection-move title="Mover selección… · Alt+M" aria-label="Mover selección">${icon('folder-open')}</button><button type="button" data-selection-melody title="Preparar consulta a Melody sobre la selección" aria-label="Consultar selección a Melody">${icon('sparkles')}</button><button type="button" data-selection-clear title="Quitar selección · Esc" aria-label="Quitar selección">${icon('close')}</button>`:''}`;
 }
 start(e){
  const row=e.target.closest('.tree-row');if(!row)return;const path=pathOf(row);
  if(!this.selected.has(path))this.selected=new Set([path]);
  this.drag={paths:[...this.selected],source:path,statusHidden:this.status.hidden};this.paint();
  document.documentElement.classList.add('explorer-dragging');
  e.dataTransfer.setData(FILES_TYPE,JSON.stringify({workspace:this.h.workspace(),paths:this.drag.paths}));e.dataTransfer.effectAllowed='move';
  const pixel=document.createElement('div');pixel.style.cssText='position:fixed;left:0;top:0;width:2px;height:2px;background:#888;opacity:.01;pointer-events:none';document.body.append(pixel);e.dataTransfer.setDragImage(pixel,0,0);setTimeout(()=>pixel.remove(),0);
  this.ghost=document.createElement('div');this.ghost.className='explorer-carry';this.ghost.setAttribute('aria-hidden','true');document.body.append(this.ghost);this.ghostHint='Arrastra para mover · Esc para cancelar';this.renderGhost();this.moveGhost(e.clientX,e.clientY,true);
  if(this.motion())this.ghost.animate([{opacity:0,scale:'.96'},{opacity:1,scale:'1'}],{duration:150,easing:'cubic-bezier(.2,.8,.2,1)'});
 }
 motion(){return document.documentElement.dataset.motion!=='off'&&!matchMedia('(prefers-reduced-motion: reduce)').matches;}
 moveGhost(x,y,now=false){
  if(!this.ghost||!Number.isFinite(x)||!Number.isFinite(y))return;
  this.rawPointer={x,y};
  const paint=()=>{this.frame=null;if(!this.ghost)return;
   const point=this.rawPointer,box=this.ghost.getBoundingClientRect(),rect=this.sidebar.getBoundingClientRect(),edge=Math.min(48,rect.height/4),x=point.x,y=point.y;
   this.pointer={x:Math.max(6,Math.min(innerWidth-box.width-10,x+18)),y:Math.max(6,Math.min(innerHeight-box.height-12,y+20))};
   this.scrollVelocity=x>=rect.left&&x<=rect.right&&y>=rect.top&&y<=rect.bottom?(y<rect.top+edge?-(1-(y-rect.top)/edge)*500:y>rect.bottom-edge?(1-(rect.bottom-y)/edge)*500:0):0;
   if(this.scrollVelocity&&!this.scrollFrame){this.scrollTime=performance.now();this.scrollFrame=requestAnimationFrame(now=>this.scrollDrag(now));}
   this.ghost.style.transform=`translate3d(${this.pointer.x}px,${this.pointer.y}px,0)`;
  };
  if(now){cancelAnimationFrame(this.frame);paint();}else if(!this.frame)this.frame=requestAnimationFrame(paint);
 }
 scrollDrag(now){
  this.scrollFrame=null;if(!this.drag||!this.scrollVelocity)return;
  const elapsed=Math.min(32,now-this.scrollTime);this.scrollTime=now;const before=this.sidebar.scrollTop;
  this.sidebar.scrollTop+=this.scrollVelocity*elapsed/1000;
  if(this.sidebar.scrollTop!==before){this.cancelHover();const point=this.rawPointer,target=document.elementFromPoint(point.x,point.y);if(target&&this.sidebar.contains(target))this.indicate(this.where({target,clientY:point.y}));this.scrollFrame=requestAnimationFrame(time=>this.scrollDrag(time));}
 }
 renderGhost(){
  if(!this.ghost||!this.drag)return;const paths=this.drag.paths,dirs=new Set(this.h.directories());this.ghost.dataset.count=String(paths.length);
  this.ghost.innerHTML=`<div class="carry-deck">${paths.slice(0,3).map((path,i)=>`<div class="carry-card" style="--card:${i}"><span>${dirs.has(path)?folderIcon(path,false):fileIcon(path)}</span><span>${esc(path.split('/').at(-1))}</span>${i===0?`<b>${paths.length}</b>`:''}</div>`).reverse().join('')}</div><small>${esc(this.ghostHint)}</small>`;
 }
 pickup(row,path){
  const rect=row.getBoundingClientRect(),glyph=row.querySelector('.file-glyph,.file-icon,.icon')||row.firstElementChild;
  this.selected.add(path);this.drag.paths=[...this.selected];this.ghostHint=path.split('/').at(-1)+' añadido a la selección';this.renderGhost();this.paint();row.classList.remove('pickup-pending');row.classList.add('pickup-added');
  if(this.motion()&&this.pointer){
   const token=document.createElement('div');token.className='explorer-pickup-token';token.innerHTML=glyph?.outerHTML||fileIcon(path);token.style.cssText=`left:${rect.left+22}px;top:${rect.top+5}px`;document.body.append(token);
   token.animate([{transform:'translate3d(0,0,0) scale(1)',opacity:.95},{transform:`translate3d(${this.pointer.x-rect.left-6}px,${this.pointer.y-rect.top+2}px,0) scale(.6)`,opacity:0}],{duration:230,easing:'cubic-bezier(.2,.75,.25,1)',fill:'forwards'}).finished.finally(()=>token.remove());
   const card=this.ghost.querySelector('.carry-card[style="--card:0"]');card?.animate([{scale:'.98'},{scale:'1.015',offset:.6},{scale:'1'}],{duration:210,easing:'ease-out'});
  }
 }
 where(e){
  const row=e.target.closest('.tree-row'),root=e.target.closest('[data-drop-root]');if(root||!row)return {kind:'move',destination:'',row:root};
  const path=pathOf(row),rect=row.getBoundingClientRect(),relative=(e.clientY-rect.top)/rect.height;
  if(relative<.24||relative>.76)return {kind:'order',target:path,after:relative>.76,row};
  if(row.hasAttribute('data-dir'))return {kind:'move',destination:path,row};
  return {kind:'pickup',path,destination:parentOf(path),row};
 }
 over(e){
  if(!this.drag)return;e.preventDefault();e.stopPropagation();const where=this.where(e);e.dataTransfer.dropEffect=this.dropIssue(this.drag,where)?'none':'move';
  this.indicate(where);
  const key=where.kind==='pickup'?where.path:null;
  if(key===this.hover)return;this.cancelHover();
  if(key&&!this.selected.has(key)){
   this.hover=key;where.row.classList.add('pickup-pending');
   this.timer=setTimeout(()=>{if(this.drag&&this.hover===key)this.pickup(where.row,key);},PICKUP_DELAY);
  }
 }
 cancelHover(){clearTimeout(this.timer);this.hover=null;this.sidebar.querySelectorAll('.pickup-pending').forEach(row=>row.classList.remove('pickup-pending'));}
 indicate(where){
  for(const row of this.sidebar.querySelectorAll('[data-drop-position]'))delete row.dataset.dropPosition;
  if(where?.row)where.row.dataset.dropPosition=where.kind==='order'?(where.after?'after':'before'):where.kind==='move'?'inside':'pickup';
  if(this.ghost&&where){const issue=this.dropIssue(this.drag,where),hint=issue|| (where.kind==='order'?(where.after?'Ordenar después':'Ordenar antes')+' de '+where.target:where.kind==='move'?'Mover a '+(where.destination||'Raíz del proyecto'):this.selected.has(where.path)?'Archivo recogido':'Mantén para recoger · 0,7 s');if(hint!==this.ghostHint){this.ghostHint=hint;const label=this.ghost.querySelector('small');if(label)label.textContent=hint;}
   const message=`${this.drag.paths.length} ${this.drag.paths.length===1?'elemento':'elementos'} · ${hint}`;if(this.destination.textContent!==message)this.destination.textContent=message;this.destination.dataset.invalid=String(!!issue);this.destination.hidden=false;
   const rect=this.sidebar.getBoundingClientRect();Object.assign(this.destination.style,{left:rect.left+'px',width:rect.width+'px'});this.destination.style.top=Math.max(rect.top,rect.bottom-this.destination.offsetHeight)+'px';}
 }
 dropIssue(drag,where){if(!drag||!where)return null;if(where.kind==='order'&&drag.paths.some(p=>parentOf(p)!==parentOf(where.target)))return 'Ordena dentro de la misma carpeta o suelta en el centro para mover';if(where.kind==='move'){const sources=drag.paths.filter(p=>p!==where.destination);if(drag.paths.includes(where.destination)&&sources.length&&sources.every(p=>this.h.directories().includes(p)))return null;if(drag.paths.some(p=>where.destination===p||where.destination.startsWith(p+'/')))return 'Elige un destino fuera de las carpetas seleccionadas';}return null;}
 finish(landing=null){
  document.documentElement.classList.remove('explorer-dragging');this.destination.hidden=true;cancelAnimationFrame(this.scrollFrame);this.scrollFrame=null;this.scrollVelocity=0;
  this.cancelHover();this.indicate();this.sidebar.querySelectorAll('.pickup-added,.is-carried').forEach(row=>row.classList.remove('pickup-added','is-carried'));this.drag=null;cancelAnimationFrame(this.frame);this.frame=null;
  const ghost=this.ghost;this.ghost=null;
  if(ghost&&landing&&this.motion()){
   const rect=landing.getBoundingClientRect();ghost.animate([{opacity:1,transform:ghost.style.transform,scale:'1'},{opacity:0,transform:`translate3d(${rect.left+30}px,${rect.top}px,0)`,scale:'.82'}],{duration:150,easing:'cubic-bezier(.2,.75,.25,1)',fill:'forwards'}).finished.finally(()=>ghost.remove());
  }else ghost?.remove();this.paint();if(this.pendingTree){this.pendingTree=false;this.h.renderTree();}
 }
 async drop(drag,where){
  const issue=this.dropIssue(drag,where);if(issue)throw Error(issue);
  if(where.kind==='pickup')return;
  if(where.kind==='order'){
   const parent=parentOf(where.target);if(drag.paths.some(p=>parentOf(p)!==parent))throw Error('Para ordenar, arrastra elementos de la misma carpeta. Para moverlos, suelta en el centro de una carpeta.');
   if(drag.paths.includes(where.target))return;
   const siblings=this.h.siblings(parent),rest=siblings.filter(p=>!drag.paths.includes(p)),index=rest.indexOf(where.target)+(where.after?1:0);rest.splice(index,0,...siblings.filter(p=>drag.paths.includes(p)));
   const before=structuredClone(this.orders),orders={...this.orders,[parent]:rest};this.orders=(await this.h.api('/platform/files/organize/layout',{orders})).orders;this.history.push({kind:'order',orders:before});this.history=this.history.slice(-16);this.h.renderTree();return;
  }
  if(drag.paths.includes(where.destination)){
   const sources=drag.paths.filter(p=>p!==where.destination);if(!sources.length)return;
   if(sources.every(p=>this.h.directories().includes(p)))return this.review(sources,where.destination,'merge');
  }
  if(drag.paths.some(p=>where.destination===p||where.destination.startsWith(p+'/')))throw Error('No puedes mover una carpeta dentro de sí misma.');
  const directories=new Set(this.h.directories());
  if(drag.paths.length>1&&drag.paths.every(p=>directories.has(p))&&where.destination){
   this.h.modal('Organizar carpetas',`<div class="organizer-review"><p>${drag.paths.length} carpetas → <strong>${esc(where.destination)}</strong></p><p class="muted-copy">Puedes conservar las carpetas dentro del destino o combinar sus contenidos. Los nombres repetidos se revisan antes de aplicar.</p><div class="modal-actions"><button class="secondary-button" data-folder-move>Mover dentro</button><button class="primary-button" data-folder-merge>${icon('folder')}Fusionar contenidos</button></div></div>`);
   document.querySelector('[data-folder-move]').onclick=()=>this.safe(()=>this.review(drag.paths,where.destination,'move'));
   document.querySelector('[data-folder-merge]').onclick=()=>this.safe(()=>this.review(drag.paths,where.destination,'merge'));return;
  }
  await this.review(drag.paths,where.destination,'move');
 }
 async review(paths,destination,mode,conflicts){
  for(const path of paths)for(const detached of this.h.editor.detachedPaths)if(detached===path||detached.startsWith(path+'/'))throw Error('Vuelve a acoplar el archivo separado antes de moverlo.');
  for(const [path,record] of this.h.editor.models)if(record.kind==='binary'&&this.h.editor.isDirty(path)&&paths.some(source=>path===source||path.startsWith(source+'/')))throw Error('Guarda o exporta los bytes pendientes antes de mover este binario.');
  const plan=await this.h.api('/platform/files/organize/plan',{paths,destination,mode,conflicts});
  if(!plan.conflicts.length&&mode==='move')return this.apply(plan);
  this.h.modal(plan.conflicts.length?'Resolver nombres repetidos':'Revisar fusión',`<div class="organizer-review"><p>${plan.moves.length} movimientos hacia <strong>${esc(destination||'Proyecto')}</strong>.</p>${plan.conflicts.length?`<p>Ya existen: ${plan.conflicts.slice(0,8).map(esc).join(', ')}. Puedes conservar ambas versiones con nombres distintos.</p>`:`<ul>${plan.moves.slice(0,12).map(row=>`<li><code>${esc(row.from)}</code><span>→</span><code>${esc(row.to)}</code></li>`).join('')}</ul>${plan.moves.length>12?`<p>Y ${plan.moves.length-12} movimientos más.</p>`:''}`}<div class="modal-actions"><button class="secondary-button" data-organizer-cancel>Cancelar</button><button class="primary-button" data-organizer-apply>${plan.conflicts.length?'Conservar ambos y revisar':'Aplicar fusión'}</button></div></div>`);
  document.querySelector('[data-organizer-cancel]').onclick=()=>this.h.closeModal();
  document.querySelector('[data-organizer-apply]').onclick=()=>this.safe(()=>plan.conflicts.length?this.review(paths,destination,mode,'keep-both'):this.apply(plan));
 }
 async apply(plan){
  this.h.closeModal();this.sidebar.setAttribute('aria-busy','true');
  try{
   const task=await this.h.api('/platform/files/organize/apply',{plan:plan.id});let result;
   while(true){const {jobs}=await this.h.api('/platform/operations'),job=jobs.find(j=>j.id===task.job);if(!job)throw Error('No se encuentra el movimiento.');if(['failed','cancelled'].includes(job.state))throw Error(job.error||'Movimiento cancelado; los archivos se han conservado.');if(job.state==='done'){result=job.result;break;}await new Promise(resolve=>setTimeout(resolve,120));}
   if(result.undoReceipt){this.history.push({kind:'move',receipt:result.undoReceipt});this.history=this.history.slice(-16);}
   await this.h.relocated(result.moved);if(!this.drag)this.selected.clear();await this.h.refreshTree();this.h.notify(`${result.moved.length} elementos movidos${result.foldersMerged?' · carpetas fusionadas: '+result.foldersMerged:''}. Puedes deshacer desde Proyecto.`);
  }finally{this.sidebar.removeAttribute('aria-busy');}
 }
 moveSelection(){
  const paths=[...this.selected];if(!paths.length||this.busy)return;
  const folders=['',...this.h.directories()].filter(folder=>!paths.some(path=>folder===path||folder.startsWith(path+'/')));
  this.h.modal('Mover selección',`<form class="organizer-destination-form"><p>${paths.length} ${paths.length===1?'elemento seleccionado':'elementos seleccionados'}</p><label class="field-label">Carpeta de destino<select name="destination">${folders.map(folder=>`<option value="${esc(folder)}">${esc(folder||'Raíz del proyecto')}</option>`).join('')}</select></label><p class="muted-copy">Los nombres repetidos se revisarán. Podrás deshacer el movimiento en esta sesión.</p><div class="modal-actions"><button type="button" class="secondary-button" data-organizer-cancel>Cancelar</button><button class="primary-button">Mover selección</button></div></form>`);
  document.querySelector('[data-organizer-cancel]').onclick=()=>this.h.closeModal();document.querySelector('.organizer-destination-form').onsubmit=e=>{e.preventDefault();this.safe(()=>this.review(paths,new FormData(e.target).get('destination'),'move'));};
 }
 async undo(){
  const entry=this.history.at(-1);if(!entry||this.busy)return;this.busy=true;this.paint();
  try{if(entry.kind==='order')this.orders=(await this.h.api('/platform/files/organize/layout',{orders:entry.orders})).orders;
   else{const task=await this.h.api('/platform/files/organize/undo',{receipt:entry.receipt});let result;while(true){const {jobs}=await this.h.api('/platform/operations'),job=jobs.find(j=>j.id===task.job);if(!job)throw Error('No se encuentra la restauración.');if(['failed','cancelled'].includes(job.state))throw Error(job.error||'Restauración cancelada.');if(job.state==='done'){result=job.result;break;}await new Promise(resolve=>setTimeout(resolve,120));}await this.h.relocated(result.moved);}
   this.history.pop();await this.h.refreshTree();this.h.renderTree();this.h.notify('Movimiento deshecho. Los cambios de contenido se conservan.');
  }finally{this.busy=false;this.paint();}
 }
 async melody(){
  const paths=[...this.selected],files=paths.filter(path=>!this.h.directories().includes(path));let text='Ayúdame a revisar y organizar esta selección del proyecto. Propón un plan antes de modificar archivos.\nSelección: '+paths.join(', ')+'\n';
  for(const path of files.slice(0,6)){
   if(path.split('/').at(-1).startsWith('.env')||/\.(pem|key|pfx)$/i.test(path))continue;
   const record=this.h.editor.models.get(path),item=record?null:await this.h.api('/file?path='+encodeURIComponent(path));const content=record?.model?.getValue()??record?.value??item?.content;
   if(typeof content==='string')text+='\nArchivo '+path+' (contenido de referencia):\n'+content.slice(0,12000)+'\n';if(text.length>48000)break;
  }
  const p=this.h.platform;p.closePage();p.host.dock.show('assistant');p.setMelodyMode?.('chat');document.querySelector('#ai-input').value=text;document.querySelector('#ai-input').focus();this.h.notify('Selección preparada para Melody. Revísala antes de enviarla.');
 }
}
