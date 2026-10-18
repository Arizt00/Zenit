import {icon,escapeHTML as esc} from './icons.js';
import {normalizeLayout} from './layout-state.js';

/** Durable project sessions. Never saves recovery text into source files. */
export class WorkbenchSession{
 constructor(host){this.host=host;this.auxiliary=new URLSearchParams(location.search).has('panel');this.queue=Promise.resolve();this.channel=new BroadcastChannel('zenit-workbench');this.restoring=false;this.disposed=false;}
 async init(){
  const h=this.host;this.workspace=h.service().workspace;
  this.data=await h.platform.api('/workbench');
  if(!this.auxiliary&&h.platform.prefs['general.restoreSession']!==false&&this.data.session)await this.restore(this.data.session,{startup:true});
  const oldChange=h.editor.callbacks.change;h.editor.callbacks.change=(...args)=>{oldChange?.(...args);this.schedule();};
  const oldActive=h.editor.callbacks.active;h.editor.callbacks.active=(...args)=>{oldActive?.(...args);this.schedule();};
  const oldCursor=h.editor.callbacks.cursor;h.editor.callbacks.cursor=(...args)=>{oldCursor?.(...args);this.schedule(1200);};
  const oldLayout=h.dock.onChange;h.dock.onChange=(...args)=>{oldLayout?.(...args);this.schedule();};
  const close=h.editor.close.bind(h.editor);h.editor.close=path=>{close(path);if(!this.restoring)this.queue=this.queue.catch(()=>{}).then(()=>h.platform.api('/workbench/discard',{path}));this.schedule();};
  window.zenitSessionSnapshot=()=>this.payload();
  this.hidden=()=>{if(document.hidden)this.flush().catch(()=>{});};document.addEventListener('visibilitychange',this.hidden);
  this.channel.onmessage=e=>{if(e.data.workspace===h.service().workspace&&e.data.type==='target')this.refreshTarget();};
  h.commands.push(['saved-spaces','workspace','Espacios: guardar y recuperar distribución',''],['execution-target','cpu','Proyecto: elegir destino de ejecución','']);
  const handle=h.desktop.handle.bind(h.desktop);h.desktop.handle=async(action,...args)=>{if(action==='saved-spaces'){await this.openSpaces();return true;}if(action==='execution-target'){await this.chooseTarget();return true;}return handle(action,...args);};
  const mark=document.querySelector('.workspace-profile-mark');if(mark){const b=document.createElement('button');b.className='workspace-profile-mark icon-button';b.type='button';b.title='Espacios guardados';b.setAttribute('aria-label','Espacios guardados');b.innerHTML=icon('workspace');b.onclick=e=>{e.preventDefault();h.platform.safe(()=>this.openSpaces());};mark.replaceWith(b);}
  if(!this.auxiliary){const b=document.createElement('button');b.type='button';b.className='icon-button saved-spaces-control';b.title='Espacios guardados';b.setAttribute('aria-label',b.title);b.innerHTML=icon('workspace');b.onclick=()=>h.platform.safe(()=>this.openSpaces());document.querySelector('.editor-tabbar .zenit-tools-menu')?.before(b);}
  this.target=document.createElement('button');this.target.type='button';this.target.className='execution-target-control secondary-button';this.target.setAttribute('aria-label','Destino de ejecución del proyecto');this.target.innerHTML=icon('cpu')+'<span>Este equipo</span>'+icon('chevron-down');this.target.onclick=()=>h.platform.safe(()=>this.chooseTarget());
  (document.querySelector('.native-heading-actions')||document.querySelector('.top-actions')).prepend(this.target);
  // Tool discovery can probe WSL; it must not delay the editor becoming usable.
  this.target.disabled=true;this.target.querySelector('span').textContent='Preparando destino…';
  this.refreshTarget().catch(error=>{if(this.disposed)return;this.target.disabled=false;this.target.querySelector('span').textContent='Revisar destino';this.target.title=error.message;});this.schedule();
 }
 capture(){
  const h=this.host,ed=h.editor,documents=[];
  for(const [path,r] of [...ed.models].slice(-48)){
   const pane=ed.panes?.find(p=>p.view?.getModel()===r.model),state=pane?.view.saveViewState()||r.viewState,position=pane?.view.getPosition()||state?.cursorState?.[0]?.position||{lineNumber:1,column:1},dirty=r.kind!=='binary'&&ed.isDirty(path);
   documents.push({path,dirty,revision:r.revision??null,...(dirty?{content:r.model?.getValue()??r.value??''}:{}),line:position.lineNumber,column:position.column,scrollTop:pane?.view.getScrollTop()??state?.viewState?.scrollTop??r.scrollTop??0,scrollLeft:pane?.view.getScrollLeft()??state?.viewState?.scrollLeft??r.scrollLeft??0});
  }
  return {documents,active:ed.current,layout:h.dock.snapshot({persistent:true}),style:h.profiles.style,panes:(ed.panes||[]).map(p=>ed.pathFor(p.view?.getModel())).filter(Boolean),axis:ed.mount.dataset.splitAxis||'horizontal'};
 }
 payload(){const ed=this.host.editor,desktop=this.host.desktop;return {workspace:this.workspace,auxiliary:this.auxiliary,session:this.capture(),shared:[...desktop.shared].filter(([path,shared])=>!desktop.pending.has(path)&&(ed.models.get(path)?.model?.getValue()??ed.models.get(path)?.value)===shared.text).map(([path])=>path)};}
 schedule(delay=650){if(this.restoring||this.disposed)return;clearTimeout(this.timer);this.timer=setTimeout(()=>this.flush().catch(e=>this.host.platform.host.notify('Recuperación de sesión: '+e.message,'error')),delay);}
 async flush(){
  clearTimeout(this.timer);if(this.disposed||this.restoring||this.workspace!==this.host.service().workspace)return;
  const payload=this.payload(),signature=JSON.stringify(payload);if(signature===this.signature)return;
  this.signature=signature;this.queue=this.queue.catch(()=>{}).then(()=>this.host.platform.api('/workbench/session',payload));
  try{return await this.queue;}catch(error){this.signature=null;throw error;}
 }
 async restore(session,{startup=false}={}){
  const h=this.host,keepActive=startup&&h.service().startup?.path?h.editor.current:null;this.restoring=true;const failures=[];
  try{
   if(session.style){await h.profiles.host.studio.save({workspaceStyle:session.style});h.profiles.apply(session.style);}
   if(session.layout&&(!startup||h.platform.prefs['general.restoreLayout']!==false)){h.dock.state=normalizeLayout(session.layout);h.dock.state.hidden=[...new Set([...h.dock.state.hidden,...h.dock.nativeDetached])];h.dock.render();}
   if(h.editor.panes?.length>1)h.editor.closeSplit();
   for(const doc of session.documents||[]){
    try{
     if(!h.editor.models.has(doc.path)){
      try{await h.openFile(doc.path);}catch(error){if(!doc.dirty)throw error;await h.openFile(doc.path,null,{path:doc.path,name:doc.path.split(/[\\/]/).pop(),content:doc.content,revision:doc.revision,newline:'LF',bom:false,transient:true});}
     }
     const r=h.editor.models.get(doc.path);
     if(doc.dirty&&r.kind!=='binary'&&!h.editor.isDirty(doc.path)){
      const conflict=r.revision!==doc.revision;h.editor.activate(doc.path);h.editor.insertText(doc.content,true);
      if(conflict){r.revision=doc.revision;r.recoveryConflict=true;failures.push(doc.path+': cambió en disco; revisa antes de guardar.');}
     }
     if(r.model&&!h.editor.detachedPaths.has(doc.path)){h.editor.activate(doc.path);const view=h.editor.view;view.setPosition({lineNumber:doc.line||1,column:doc.column||1});view.setScrollPosition({scrollTop:doc.scrollTop||0,scrollLeft:doc.scrollLeft||0});r.viewState=view.saveViewState();}
    }catch(error){failures.push(doc.path+': '+error.message);}
   }
   const panes=(session.panes||[]).filter(p=>h.editor.models.get(p)?.model&&!h.editor.detachedPaths.has(p));if(panes[0])h.editor.activate(panes[0]);if(panes.length>1)h.editor.split(panes[1],session.axis==='vertical'?'bottom':'right');
   for(const pane of h.editor.panes||[]){const r=h.editor.models.get(h.editor.pathFor(pane.view.getModel()));if(r?.viewState)pane.view.restoreViewState(r.viewState);}
   const active=keepActive||session.active,activePane=h.editor.panes?.find(p=>h.editor.pathFor(p.view.getModel())===active);if(activePane){h.editor.view=activePane.view;activePane.view.focus();}if(h.editor.models.has(active))await h.openFile(active);
   h.renderTabs();
   if(failures.length)h.platform.host.notify('Sesión recuperada. '+failures.slice(0,3).join(' · '),'info',10000);
  }finally{this.restoring=false;}
 }
 async workspaceChanged(){clearTimeout(this.timer);this.workspace=this.host.service().workspace;this.signature=null;this.data=await this.host.platform.api('/workbench');if(!this.auxiliary&&this.host.platform.prefs['general.restoreSession']!==false&&this.data.session)await this.restore(this.data.session);await this.refreshTarget();this.schedule();}
 async openSpaces(){
  const h=this.host,p=h.platform;this.data=await p.api('/workbench');
  p.host.modal('Espacios de trabajo',`<div class="saved-spaces-sheet"><p class="muted-copy">Guarda los paneles, las pestañas y el estilo de este proyecto. Los cambios sin guardar permanecen en la recuperación de sesión.</p><form class="saved-space-form"><label>Nombre del espacio<input name="name" maxlength="60" placeholder="Mi espacio de programación" required></label><button class="primary-button">${icon('check')}Guardar espacio actual</button></form><div class="saved-space-list">${this.data.spaces.map((s,i)=>`<article><span>${icon('workspace')}</span><div><strong>${esc(s.name)}</strong><small>${s.session.documents.length} archivos · ${esc(s.session.style)}</small></div><button class="secondary-button" data-space-open="${i}">Abrir</button><button class="icon-button" data-space-delete="${i}" aria-label="Eliminar espacio ${esc(s.name)}">${icon('trash')}</button></article>`).join('')||'<p class="muted-copy">Guarda tu primera distribución para recuperarla cuando la necesites.</p>'}</div><p class="saved-space-status" role="status"></p></div>`,{wide:true});
  document.querySelector('.saved-space-form').onsubmit=e=>{e.preventDefault();p.safe(async()=>{await p.api('/workbench/spaces/save',{name:new FormData(e.target).get('name'),session:this.capture()});await this.openSpaces();});};
  document.querySelectorAll('[data-space-open]').forEach(b=>b.onclick=()=>p.safe(async()=>{const session=this.data.spaces[+b.dataset.spaceOpen].session;await this.flush();p.host.closeModal();for(const path of [...h.editor.models.keys()])if(!h.editor.isDirty(path)&&!session.documents.some(d=>d.path===path))h.editor.close(path);await this.restore(session);await this.flush();}));
  document.querySelectorAll('[data-space-delete]').forEach(b=>b.onclick=()=>p.safe(async()=>{await p.api('/workbench/spaces/delete',{name:this.data.spaces[+b.dataset.spaceDelete].name});await this.openSpaces();}));
 }
 async refreshTarget(){if(this.disposed)return;this.targets=await this.host.platform.api('/execution/targets');if(this.disposed)return;const selected=this.targets.targets.find(t=>t.id===this.targets.selected);if(this.target){this.target.disabled=false;this.target.querySelector('span').textContent=selected?.label||'Destino no disponible';this.target.title='Ejecutar en '+(selected?.label||'destino no disponible');this.target.dataset.available=String(!!selected?.available);}}
 async chooseTarget(){
  await this.refreshTarget();const h=this.host;
  h.platform.host.showMenu(this.target,this.targets.targets.map(t=>({label:t.label,icon:t.kind==='local'?'cpu':t.kind==='wsl'?'terminal':'cube',disabled:!t.available,run:()=>h.platform.safe(async()=>{
   if(!await h.platform.host.ensureTrust())return;
   if(t.kind==='ssh')return this.configureSSH(t);
   await h.platform.api('/execution/select',{id:t.id});await this.refreshTarget();this.channel.postMessage({type:'target',workspace:h.service().workspace});
  })})),'Destino de ejecución');
 }
 configureSSH(target){
  const h=this.host,p=h.platform;
  p.host.modal('Proyecto en '+target.label,`<p>Los archivos guardados del proyecto deben existir en esta carpeta de la estación. Las herramientas se ejecutan allí mediante OpenSSH.</p><form id="remote-workspace-form"><label class="field-label">Carpeta remota<input name="directory" required value="${esc(this.targets.options?.directory||'')}" placeholder="/home/usuario/proyecto"></label><button class="primary-button">Usar este destino</button></form>`);
  document.querySelector('#remote-workspace-form').onsubmit=e=>{e.preventDefault();p.safe(async()=>{await p.api('/execution/select',{id:target.id,directory:new FormData(e.target).get('directory')});p.host.closeModal();await this.refreshTarget();this.channel.postMessage({type:'target',workspace:h.service().workspace});});};
 }
 dispose(){this.flush().catch(()=>{});this.disposed=true;clearTimeout(this.timer);this.channel.close();document.removeEventListener('visibilitychange',this.hidden);delete window.zenitSessionSnapshot;}
}
