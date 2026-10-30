import {icon,fileIcon,escapeHTML as esc} from './icons.js';
import {languageFor} from './editor.js';

export class GitWorkbenchUI{
 constructor(h){this.h=h;this.generation=0;}
 async open(){this.mode='page';await this.render();}
 async sidebar(){this.mode='sidebar';await this.render();}
 async render(){
  const h=this.h,p=h.platform,workspace=h.service().workspace,epoch=++this.generation,state=await p.api('/git/changes');
  if(workspace!==h.service().workspace||epoch!==this.generation||this.mode==='sidebar'&&document.querySelector('.rail-item[data-view=git]')?.classList.contains('active')!==true)return;
  const group=(label,scope,rows)=>`<section class="git-change-group"><header><strong>${label}</strong><small>${rows.length}</small></header>${rows.map(row=>`<button class="git-file-change" data-git-path="${esc(row.path)}" data-git-scope="${scope}" title="${esc(row.oldPath?row.oldPath+' → '+row.path:row.path)}">${fileIcon(row.path)}<span><strong>${esc(row.path.split('/').pop())}</strong><small>${esc(row.oldPath?row.oldPath+' → '+row.path:row.path)}</small></span><code>${esc(row.status)}</code></button>`).join('')||'<p class="muted-copy">Sin cambios</p>'}</section>`;
  const markup=`<section class="git-workspace ${this.mode==='sidebar'?'git-compact':''}"><header class="git-state-heading"><span>${icon('git')}<strong>${esc(state.branch||'Repositorio local')}</strong></span><button class="icon-button" data-git-refresh aria-label="Actualizar Git">${icon('refresh')}</button></header>${state.available?group('Cambios preparados','staged',state.files.filter(r=>r.staged&&!r.conflict))+group('Cambios de trabajo','working',state.files.filter(r=>r.working&&!r.conflict))+group('Conflictos','conflict',state.files.filter(r=>r.conflict)):`<p class="git-state-error" id="git-output">${esc(state.message)}</p>`}<p class="git-state-note">Cada acción revisa un archivo. Preparar y retirar cambios modifica el índice local.</p></section>`;
  if(this.mode==='sidebar'){document.querySelector('#sidebar-title').textContent='Control de versiones';document.querySelector('#sidebar-content').innerHTML=markup;this.root=document.querySelector('#sidebar-content .git-workspace');}
  else{p.openPage('git',`<div class="platform-content">${markup}</div>`);this.root=p.workbench.querySelector('.git-workspace');}
  this.root.querySelector('[data-git-refresh]').onclick=()=>p.safe(()=>this.render());
  this.root.querySelectorAll('[data-git-path]').forEach(button=>button.onclick=()=>p.safe(()=>button.dataset.gitScope==='conflict'?p.conflictsUI.open():this.preview(button.dataset.gitPath,button.dataset.gitScope)));
 }
 async preview(path,scope){
  const h=this.h,p=h.platform,workspace=h.service().workspace,origin=this.root;
  if(!await p.host.ensureTrust())return;
  if(scope==='working'&&h.editor.isDirty(path))throw Error('Guarda los cambios de este archivo antes de preparar su versión en Git.');
  const plan=await p.api('/git/preview',{path,scope});if(workspace!==h.service().workspace||!origin?.isConnected)return;this.disposeDiff();
  h.modal('Git · '+(scope==='working'?'revisar cambios de trabajo':'revisar cambios preparados'),`<section class="git-change-review"><header>${fileIcon(path)}<div><strong>${esc(path)}</strong><small>${scope==='working'?'Índice → archivo guardado':'HEAD → índice'}</small></div></header>${plan.oldPath?`<p>${esc(plan.oldPath)} → ${esc(path)}</p>`:''}${plan.binary?`<p>Archivo binario: ${plan.beforeBytes} → ${plan.afterBytes} bytes. No hay una vista de texto fiable.</p>`:'<div class="git-diff-editor"></div>'}<p data-git-status role="status"></p><div class="modal-actions"><button class="secondary-button" data-git-source>${icon('file')}Abrir archivo</button><button class="primary-button" data-git-apply>${icon(scope==='working'?'plus':'undo')}${scope==='working'?'Preparar este cambio':'Retirar del índice'}</button></div></section>`,{wide:true});
  const owner=document.querySelector('.git-change-review');
  if(!plan.binary&&window.monaco){const m=window.monaco;this.diffModels=[m.editor.createModel(plan.before,languageFor(path)),m.editor.createModel(plan.after,languageFor(path))];this.diff=m.editor.createDiffEditor(owner.querySelector('.git-diff-editor'),{readOnly:true,originalEditable:false,automaticLayout:true,renderSideBySide:innerWidth>900,minimap:{enabled:false},scrollBeyondLastLine:false,fontSize:h.editor.settings.fontSize||13,renderIndicators:true});this.diff.setModel({original:this.diffModels[0],modified:this.diffModels[1]});}
  this.observer=new MutationObserver(()=>{if(!owner.isConnected)this.disposeDiff();});this.observer.observe(document.body,{childList:true,subtree:true});
  owner.querySelector('[data-git-source]').onclick=()=>p.safe(async()=>{h.closeModal();p.closePage();await h.openFile(path);});
  owner.querySelector('[data-git-apply]').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{
   if(scope==='working'&&h.editor.isDirty(path))throw Error('El búfer cambió. Guárdalo y revisa de nuevo Git.');
   await p.api('/git/index',{plan:plan.id,consent:true});h.closeModal();h.notify(scope==='working'?'Cambio preparado en el índice.':'Cambio retirado del índice.');await this.render();
  }catch(error){if(owner.isConnected){owner.querySelector('[data-git-status]').textContent=error.message;button.disabled=false;}}};
 }
 disposeDiff(){this.observer?.disconnect();this.observer=null;this.diff?.dispose();this.diff=null;for(const m of this.diffModels||[])m.dispose();this.diffModels=[];}
 dispose(){this.generation++;this.disposeDiff();}
}
