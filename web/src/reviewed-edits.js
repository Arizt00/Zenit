import {icon,escapeHTML as esc} from './icons.js';

export function changeExcerpt(before,after){
 const a=before.split('\n'),b=after.split('\n');let start=0,end=0;
 while(start<Math.min(a.length,b.length)&&a[start]===b[start])start++;
 while(end<Math.min(a.length,b.length)-start&&a.at(-end-1)===b.at(-end-1))end++;
 const context=a.slice(Math.max(0,start-2),start).map(x=>'  '+x),removed=a.slice(start,a.length-end).map(x=>'− '+x),added=b.slice(start,b.length-end).map(x=>'+ '+x);
 return [...context,...removed,...added,...a.slice(a.length-end,a.length-end+2).map(x=>'  '+x)].slice(0,160).join('\n').slice(0,16000);
}

export class ReviewedEdits{
 constructor(h){this.h=h;this.pending=null;}
 uriPath(uri){
  const raw=typeof uri==='string'?uri:uri?.external||uri?.fsPath||uri?.path||'',root=this.h.service().workspace.replaceAll('\\','/').replace(/\/$/,'');
  const path=decodeURIComponent(raw.replace(/^file:\/\//,'')).replaceAll('\\','/').replace(/^\/([A-Za-z]:)/,'$1');
  const windows=/^[A-Za-z]:/.test(root),inside=windows?path.toLowerCase().startsWith(root.toLowerCase()+'/'):path.startsWith(root+'/');
  const relative=inside?path.slice(root.length+1):path;
  if(!relative||/^(?:[A-Za-z]:|\/)/.test(relative)||relative.includes('\0')||relative.split('/').some(p=>p==='..'||p==='.git'||p==='.lumen'))throw Error('La edición sale de los archivos de código del proyecto.');
  return relative;
 }
 async workspaceChanges(edit,source,version){
  const groups=new Map(),m=window.monaco,ed=this.h.editor;
  const add=(uri,edits)=>{const path=this.uriPath(uri);if(!groups.has(path))groups.set(path,[]);groups.get(path).push(...edits);};
  if(Array.isArray(edit?.changes))for(const row of edit.changes)add(row.uri,row.edits);
  else for(const [uri,edits] of Object.entries(edit?.changes||{}))add(uri,edits);
  for(const row of edit?.documentChanges||[]){if(!row.textDocument)throw Error('La acción modifica recursos. Utiliza la revisión de archivos de la extensión.');add(row.textDocument.uri,row.edits);}
  if(edit?.operations?.some(o=>o.kind!=='text'))throw Error('La acción modifica recursos y necesita su revisión específica.');
  if(groups.size>64)throw Error('Revisa hasta 64 archivos por refactorización.');
  const changes=[];
  for(const [path,edits] of groups){
   let record=ed.models.get(path);
   if(!record){const item=await this.h.api('/file?path='+encodeURIComponent(path));ed.open(item,{activate:false});record=ed.models.get(path);this.h.renderTabs();}
   if(!record.model||record.kind==='binary')throw Error('La acción necesita un documento de texto: '+path);
   const model=record.model,before=model.getValue(),operations=[];
   for(const edit of edits){
    const r=edit.range,range=new m.Range(r.start.line+1,r.start.character+1,r.end.line+1,r.end.character+1);
    if(typeof edit.newText!=='string'||!m.Range.equalsRange(range,model.validateRange(range)))throw Error('La acción devolvió una posición no válida.');
    operations.push({start:model.getOffsetAt(range.getStartPosition()),end:model.getOffsetAt(range.getEndPosition()),text:edit.newText});
   }
   operations.sort((a,b)=>a.start-b.start||a.end-b.end);let at=0,after='';
   for(const op of operations){if(op.start<at)throw Error('La acción contiene cambios solapados.');after+=before.slice(at,op.start)+op.text;at=op.end;}after+=before.slice(at);
   if(after!==before)changes.push({path,before,after,revision:record.revision});
  }
  if(source&&(source.isDisposed()||source.getVersionId()!==version))throw Error('El archivo cambió mientras se preparaba la acción. Solicítala de nuevo.');
  return changes;
 }
 async reviewWorkspace(edit,source,version,title='Revisar refactorización',options={}){
  if(options.verify)await options.verify();
  const changes=await this.workspaceChanges(edit,source,version),result=await this.review(changes,{title,...options});
  if(result.edits.length)this.trackNative(changes);return result;
 }
 trackNative(changes){
  const rows=changes.map(c=>({model:this.h.editor.models.get(c.path).model,before:c.before,after:c.after})),workspace=this.h.service().workspace,subscriptions=[];
  let timer;const dispose=()=>{clearTimeout(timer);subscriptions.forEach(s=>s.dispose());};
  const capture=()=>{if(rows.every(r=>!r.model.isDisposed()&&r.model.getValue()===r.after)){dispose();this.last={workspace,rows:rows.map(r=>({...r,afterVersion:r.model.getAlternativeVersionId()})),state:'applied'};}};
  for(const row of rows)subscriptions.push(row.model.onDidChangeContent(capture));timer=setTimeout(dispose,5000);capture();
 }
 async review(changes,{title='Revisar cambios',verify=null}={}){
  if(this.pending)throw Error('Termina la revisión de cambios que está abierta.');
  if(!changes.length){this.h.notify('La acción no produjo cambios de texto.');return {edits:[]};}
  const encoder=new TextEncoder();
  if(changes.length>64||changes.reduce((n,c)=>n+encoder.encode(c.before).length+encoder.encode(c.after).length,0)>4*1024*1024)throw Error('La revisión admite hasta 64 archivos y 4 MiB de texto.');
  const h=this.h,ed=h.editor,workspace=h.service().workspace,records=[];
  for(const c of changes){
   let record=ed.models.get(c.path);if(!record){const item=await h.api('/file?path='+encodeURIComponent(c.path));ed.open(item,{activate:false});record=ed.models.get(c.path);h.renderTabs();}
   if(!record.model||record.model.getValue()!==c.before)throw Error('Cambió el búfer de '+c.path+'. Vuelve a revisar.');
   records.push({change:c,model:record.model,version:record.model.getVersionId()});
  }
  const guard=()=>{if(workspace!==h.service().workspace||records.some(r=>r.model.isDisposed()||r.model.getVersionId()!==r.version))throw Error('Un búfer cambió durante la revisión. Tus cambios se conservan; prepara otra revisión.');};
  h.modal(title,`<section class="editor-change-review"><p>${changes.length} archivos. Se aplicará el conjunto al editor y podrás deshacerlo. El guardado respeta tus ajustes habituales.</p><div class="editor-change-list">${changes.map(c=>`<details open><summary>${icon('file')}<strong>${esc(c.path)}</strong>${c.count?`<small>${c.count} reemplazos</small>`:''}</summary><pre>${esc(changeExcerpt(c.before,c.after))}</pre></details>`).join('')}</div><p class="editor-change-status" role="status"></p><div class="modal-actions"><button class="secondary-button" data-review-cancel>Cancelar</button><button class="primary-button" data-review-apply>${icon('check')}Aplicar conjunto</button></div></section>`,{wide:true});
  const owner=document.querySelector('.editor-change-review');
  return new Promise(resolve=>{
   const finish=value=>{observer.disconnect();if(this.pending?.owner===owner)this.pending=null;resolve(value);};
   const observer=new MutationObserver(()=>{if(!owner.isConnected)finish({edits:[]});});observer.observe(document.body,{childList:true,subtree:true});this.pending={owner};
   owner.querySelector('[data-review-cancel]').onclick=()=>{finish({edits:[]});h.closeModal();};
   owner.querySelector('[data-review-apply]').onclick=async e=>{
    const button=e.currentTarget;button.disabled=true;
    try{guard();await h.platform.api('/editor/revisions',{documents:changes.map(c=>({path:c.path,revision:c.revision}))});if(verify)await verify();guard();
     const edits=records.map(({model,change,version})=>({resource:model.uri,versionId:version,textEdit:{range:model.getFullModelRange(),text:change.after}}));
     finish({edits});h.closeModal();
    }catch(error){if(owner.isConnected){owner.querySelector('[role=status]').textContent=error.message;button.disabled=false;}}
   };
  });
 }
 async apply(changes,options={}){
  const result=await this.review(changes,options),ed=this.h.editor;
  if(!result.edits.length)return false;
  const records=result.edits.map(e=>({edit:e,model:[...ed.models.values()].find(r=>r.model?.uri.toString()===e.resource.toString())?.model}));
  if(records.some(r=>!r.model||r.model.getVersionId()!==r.edit.versionId))throw Error('La edición caducó antes de aplicarse.');
  const receipt=[];
  try{for(const {model,edit} of records){const before=model.getValue();model.pushStackElement();model.pushEditOperations([],[{range:edit.textEdit.range,text:edit.textEdit.text}],()=>null);model.pushStackElement();receipt.push({model,before,after:model.getValue(),afterVersion:model.getAlternativeVersionId()});}}
  catch(error){for(const row of receipt.reverse())await row.model.undo();throw error;}
  this.last={workspace:this.h.service().workspace,rows:receipt,state:'applied'};this.h.renderTabs();this.h.notify('Conjunto aplicado. Ctrl+Z o «Deshacer conjunto revisado» restaura sus archivos.');return true;
 }
 canRestore(direction){
  const last=this.last,key=direction==='undo'?'after':'before',state=direction==='undo'?'applied':'undone';
  return !!last&&last.workspace===this.h.service().workspace&&last.state===state&&last.rows.every(r=>!r.model.isDisposed()&&!this.h.ownsShared?.(this.h.editor.pathFor(r.model))&&r.model.getValue()===r[key]&&r.model.getAlternativeVersionId()===r[key+'Version']);
 }
 async undo(){
  const last=this.last;if(!last||last.workspace!==this.h.service().workspace)throw Error('No hay un conjunto revisado en este proyecto.');
  if(!this.canRestore('undo'))throw Error('Hay cambios posteriores. Usa Deshacer en cada archivo para conservarlos.');
  for(const row of last.rows){await row.model.undo();row.beforeVersion=row.model.getAlternativeVersionId();}
  last.state='undone';this.h.renderTabs();this.h.notify('Conjunto restaurado.');
 }
 async redo(){
  if(!this.canRestore('redo'))throw Error('El conjunto cambió después de deshacerlo.');
  for(const row of this.last.rows){await row.model.redo();row.afterVersion=row.model.getAlternativeVersionId();}
  this.last.state='applied';this.h.renderTabs();this.h.notify('Conjunto aplicado de nuevo.');
 }
}
