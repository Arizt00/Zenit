import {icon,escapeHTML as esc} from './icons.js';
import {languageFor} from './editor.js';

/** Completed model proposals are data; a reviewed ticket is the only disk action. */
export class MelodyFilesUI{
  constructor(platform){this.platform=platform;this.host=platform.host;}
  record(path){const normalize=p=>{const name=p.replace(/\\/g,'/');return /^[a-z]:\//i.test(name)?name.toLowerCase():name;};const key=[...this.host.editor.models.keys()].find(key=>normalize(key)===normalize(path));return this.host.editor.models.get(key);}
  read(path){const query='?path='+encodeURIComponent(path);return /^(?:[A-Za-z]:[\\/]|\/)/.test(path)?this.platform.api('/extensions/file'+query):this.host.api('/file'+query);}
  request(){const input=document.getElementById('ai-input');input.value=this.platform.t('Crea un proyecto completo en una nueva carpeta con ','Create a complete project in a new folder with ');input.focus();this.host.notify(this.platform.t('Puedes crear un proyecto, modificar un archivo o pedir su borrado por nombre. Cada cambio conserva recuperación y deshacer.','Create a project, edit a file, or request deletion by name. Changes retain recovery and undo.'));}
  async capture(){
    const desktop=this.host.studio?.desktop;
    if(desktop){for(const path of this.host.editor.models.keys())await desktop.share(path);await desktop.publish();await desktop.bufferWrites;}
  }
  async review(job,element){
    const plan=await this.platform.api('/ai/files/review',{job});
    element.textContent='';const summary=document.createElement('p');summary.textContent=plan.summary||'Propuesta de archivos';element.append(summary);
    const list=document.createElement('ul');list.className='melody-plan-paths';for(const op of plan.operations){const item=document.createElement('li');item.textContent=({create:'Crear',update:'Actualizar',delete:'Borrar'})[op.kind]+' · '+op.path;list.append(item);}element.append(list);
    const button=document.createElement('button');button.className='secondary-button';button.innerHTML=icon('files')+'Revisar '+plan.operations.length+' archivos';button.onclick=()=>this.platform.safe(()=>this.open(plan,element));element.append(button);
    if(plan.direct&&this.platform.prefs['security.confirmRoutineActions']===false)await this.apply(plan,element);
  }
  async clean(plan,undo=false){
    const ed=this.host.editor;
    for(const op of plan.operations){const r=this.record(op.path);if(!r)continue;const text=r.model?.getValue()??r.value;
      if(undo?ed.isDirty(r.path):text.replace(/\r\n/g,'\n')!==op.before.replace(/\r\n/g,'\n'))throw Error('El archivo cambió después de la petición: '+op.path+'. Tu edición se conserva.');}
    const desktop=this.host.studio?.desktop;await desktop?.publish();await desktop?.bufferWrites;
  }
  open(plan,element){
    this.host.modal('Melody · revisar archivos',`<section class="melody-file-review"><p>${esc(plan.summary)}</p><small class="melody-plan-workspace">${esc(plan.workspace)}</small><p class="form-hint">Se escribirán estos archivos en disco. Los borrados y contenidos anteriores tendrán una copia en .lumen/melody. Revisa el código; generar un proyecto no acredita que compile.</p><div class="melody-plan-files">${plan.operations.map((op,i)=>`<details ${i===0?'open':''}><summary><span class="melody-plan-kind" data-kind="${op.kind}">${({create:'Crear',update:'Actualizar',delete:'Borrar'})[op.kind]}</span><strong>${esc(op.path)}</strong></summary>${op.kind!=='create'?`<label>Actual</label><pre>${esc(op.before)}</pre>`:''}${op.kind!=='delete'?`<label>Propuesto</label><pre>${esc(op.content)}</pre>`:''}</details>`).join('')}</div><p class="error-message" role="alert" id="melody-plan-error"></p><div class="modal-actions"><button class="secondary-button" data-action="close-modal">Cancelar</button><button class="primary-button" id="melody-plan-apply">Aplicar ${plan.operations.length} cambios</button></div></section>`,{wide:true});
    document.getElementById('melody-plan-apply').onclick=async event=>{
      const button=event.currentTarget;button.disabled=true;
      try{await this.apply(plan,element);this.host.closeModal();
      }catch(error){const target=document.getElementById('melody-plan-error');if(target)target.textContent=error.message;else this.host.notify(error.message,'error');button.disabled=false;}
    };
    if(window.monaco){for(const [index,details] of [...document.querySelectorAll('.melody-plan-files details')].entries()){
      const op=plan.operations[index];if(op.kind==='delete')continue;const button=document.createElement('button');button.className='text-button melody-diff-toggle';button.type='button';button.innerHTML=icon('split')+'Comparar cambios';details.append(button);
      button.onclick=()=>{if(details.querySelector('.melody-diff'))return;const mount=document.createElement('div');mount.className='melody-diff';details.append(mount);const editor=monaco.editor.createDiffEditor(mount,{readOnly:true,automaticLayout:true,renderSideBySide:innerWidth>800,minimap:{enabled:false},scrollBeyondLastLine:false,originalEditable:false,fontSize:12});const original=monaco.editor.createModel(op.before||'',languageFor(op.path)),modified=monaco.editor.createModel(op.content||'',languageFor(op.path));editor.setModel({original,modified});button.hidden=true;for(const source of details.querySelectorAll(':scope>pre,:scope>label'))source.hidden=true;
        const observer=new MutationObserver(()=>{if(!mount.isConnected){editor.dispose();original.dispose();modified.dispose();observer.disconnect();}});observer.observe(document.body,{childList:true,subtree:true});};
    }}
  }
  async apply(plan,element){
    await this.clean(plan);const captured=new Map(plan.operations.map(op=>{const r=this.record(op.path);return [op.path,r?{record:r,text:r.model?.getValue()??r.value}:null];}));
    const result=await this.platform.api('/ai/files/apply',{ticket:plan.ticket,consent:true});
    await this.reload(result.operations.map(x=>x.path),captured).catch(error=>this.host.notify('Cambios guardados; revisa la sincronización del editor: '+error.message,'error'));
    element.textContent='';element.classList.add('melody-applied');
    const title=document.createElement('strong');title.innerHTML=icon('check')+(result.operations.length===1?'Aplicado 1 cambio':'Aplicados '+result.operations.length+' cambios');element.append(title);
    const paths=document.createElement('ul');paths.className='melody-plan-paths';for(const op of result.operations){const li=document.createElement('li');li.textContent=({create:'Creado',update:'Actualizado',delete:'Borrado'})[op.kind]+' · '+op.path;paths.append(li);}element.append(paths);
    const recovery=document.createElement('small');recovery.className='melody-recovery';recovery.textContent='Copia de recuperación: '+result.recovery;element.append(recovery);
    const actions=document.createElement('div');actions.className='melody-file-actions';element.append(actions);
    const review=document.createElement('button');review.className='text-button';review.innerHTML=icon('files')+'Ver cambios';review.onclick=()=>this.showApplied(plan);actions.append(review);
    const undo=document.createElement('button');undo.className='secondary-button';undo.innerHTML=icon('refresh')+'Deshacer este plan';undo.onclick=()=>this.platform.safe(async()=>{undo.disabled=true;try{await this.clean(plan,true);const captured=new Map(plan.operations.map(op=>{const r=this.record(op.path);return [op.path,r?{record:r,text:r.model?.getValue()??r.value}:null];}));const restored=await this.platform.api('/ai/files/undo',{receipt:result.receipt});await this.reload(restored.operations.map(x=>x.path),captured,true);element.textContent='Plan deshecho. Se han restaurado los contenidos y los cambios sin guardar anteriores.';}finally{undo.disabled=false;}});actions.append(undo);
    const first=plan.operations.find(x=>x.kind==='create');if(first)await this.host.openFile(first.path);
  }
  showApplied(plan){
    this.open(plan,document.createElement('div'));const button=document.getElementById('melody-plan-apply');button?.remove();document.querySelector('.melody-file-review .form-hint').textContent='Estos cambios ya se aplicaron. Puedes deshacer el plan desde la conversación.';
  }
  async reload(paths,captured=null,restore=false){
    const ed=this.host.editor;
    const desktop=this.host.studio?.desktop,data=await this.platform.api('/buffers');
    for(const path of paths){const remote=data.buffers.find(x=>x.path===path||x.path.replace(/\\/g,'/')===path);let record=this.record(path);
      if(!record&&restore&&remote){await this.host.openFile(path);record=this.record(path);}if(!record)continue;const key=record.path;
      const before=captured?.get(path),text=record.model?.getValue()??record.value;
      if(before&&(record!==before.record||text!==before.text&&text!==remote?.text)||!before&&ed.isDirty(key)&&text!==remote?.text){this.host.notify('Conserva los cambios locales de '+path+'; revisa el contenido en disco.','error');continue;}
      const version=record.model?.getVersionId();let item;try{item=await this.read(path);}catch(error){if(error.status===404||/encuentra|existe/i.test(error.message)){if(restore&&remote)item={content:'',revision:null,newline:record.newline||'LF',bom:false};else{if(before||!ed.isDirty(key)){desktop?.shared.delete(key);desktop?.pending.delete(key);ed.close(key);}continue;}}else throw error;}
      if(this.record(path)!==record||record.model&&record.model.getVersionId()!==version)continue;
      record.savedValue=item.content;record.value=item.content;record.revision=item.revision;record.newline=item.newline;record.bom=item.bom;
      const next=remote?.text??item.content;
      if(remote&&desktop){desktop.shared.set(key,remote);desktop.pending.delete(key);}
      if(desktop)desktop.applying=true;try{if(record.model&&record.model.getValue()!==next){record.model.pushStackElement();record.model.pushEditOperations([],[{range:record.model.getFullModelRange(),text:next}],()=>null);record.model.pushStackElement();}else if(!record.model&&ed.current===key)ed.setValue(next);record.value=next;}finally{if(desktop)desktop.applying=false;}
    }
    this.host.refreshFileViews();await this.host.refreshTree?.();
  }
}
