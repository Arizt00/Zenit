import {icon,escapeHTML as esc} from './icons.js';

/** Completed model proposals are data; a reviewed ticket is the only disk action. */
export class MelodyFilesUI{
  constructor(platform){this.platform=platform;this.host=platform.host;}
  request(){const input=document.getElementById('ai-input');input.value='Crea un proyecto completo en una nueva carpeta con ';input.focus();this.host.notify('Describe el proyecto o pide crear/borrar archivos. Melody mostrará el plan antes de escribir.');}
  async review(job,element){
    const plan=await this.platform.api('/ai/files/review',{job});
    element.textContent='';const summary=document.createElement('p');summary.textContent=plan.summary||'Propuesta de archivos';element.append(summary);
    const list=document.createElement('ul');list.className='melody-plan-paths';for(const op of plan.operations){const item=document.createElement('li');item.textContent=({create:'Crear',update:'Actualizar',delete:'Borrar'})[op.kind]+' · '+op.path;list.append(item);}element.append(list);
    const button=document.createElement('button');button.className='secondary-button';button.innerHTML=icon('files')+'Revisar '+plan.operations.length+' archivos';button.onclick=()=>this.platform.safe(()=>this.open(plan,element));element.append(button);
  }
  async clean(plan){
    const ed=this.host.editor;
    for(const op of plan.operations)if(ed.models.has(op.path)&&ed.isDirty(op.path))throw Error('Hay cambios sin guardar en '+op.path+'. Guárdalos antes de aplicar el plan.');
    const desktop=this.host.studio?.desktop;await desktop?.publish();await desktop?.bufferWrites;
  }
  open(plan,element){
    this.host.modal('Melody · revisar archivos',`<section class="melody-file-review"><p>${esc(plan.summary)}</p><small class="melody-plan-workspace">${esc(plan.workspace)}</small><p class="form-hint">Se escribirán estos archivos en disco. Los borrados y contenidos anteriores tendrán una copia en .lumen/melody. Revisa el código; generar un proyecto no acredita que compile.</p><div class="melody-plan-files">${plan.operations.map((op,i)=>`<details ${i===0?'open':''}><summary><span class="melody-plan-kind" data-kind="${op.kind}">${({create:'Crear',update:'Actualizar',delete:'Borrar'})[op.kind]}</span><strong>${esc(op.path)}</strong></summary>${op.kind!=='create'?`<label>Actual</label><pre>${esc(op.before)}</pre>`:''}${op.kind!=='delete'?`<label>Propuesto</label><pre>${esc(op.content)}</pre>`:''}</details>`).join('')}</div><p class="error-message" role="alert" id="melody-plan-error"></p><div class="modal-actions"><button class="secondary-button" data-action="close-modal">Cancelar</button><button class="primary-button" id="melody-plan-apply">Aplicar ${plan.operations.length} cambios</button></div></section>`,{wide:true});
    document.getElementById('melody-plan-apply').onclick=async event=>{
      const button=event.currentTarget;button.disabled=true;
      try{await this.clean(plan);const result=await this.platform.api('/ai/files/apply',{ticket:plan.ticket,consent:true});button.remove();this.host.closeModal();await this.reload(result.operations.map(x=>x.path));
        element.textContent='Aplicados '+result.operations.length+' cambios. Copia de recuperación: '+result.recovery;
        const undo=document.createElement('button');undo.className='secondary-button';undo.innerHTML=icon('refresh')+'Deshacer este plan';undo.onclick=()=>this.platform.safe(async()=>{await this.clean(plan);const restored=await this.platform.api('/ai/files/undo',{receipt:result.receipt});await this.reload(restored.operations.map(x=>x.path));element.textContent='Plan deshecho. Se han restaurado los contenidos anteriores.';});element.append(undo);
        const first=plan.operations.find(x=>x.kind==='create');if(first)await this.host.openFile(first.path);
      }catch(error){const target=document.getElementById('melody-plan-error');if(target)target.textContent=error.message;else this.host.notify(error.message,'error');button.disabled=false;}
    };
  }
  async reload(paths){
    const ed=this.host.editor;
    for(const path of paths){const record=ed.models.get(path);if(!record)continue;if(ed.isDirty(path)){this.host.notify('Conserva los cambios locales de '+path+'; revisa el contenido en disco.','error');continue;}
      const version=record.model?.getVersionId();let item;try{item=await this.host.api('/file?path='+encodeURIComponent(path));}catch(error){if(error.status===404||/encuentra|existe/i.test(error.message)){if(!ed.isDirty(path))ed.close(path);continue;}throw error;}
      if(ed.models.get(path)!==record||ed.isDirty(path)||record.model&&record.model.getVersionId()!==version)continue;
      record.savedValue=item.content;record.value=item.content;record.revision=item.revision;record.newline=item.newline;record.bom=item.bom;
      if(record.model&&record.model.getValue()!==item.content){record.model.setValue(item.content);}else if(!record.model&&ed.current===path)ed.setValue(item.content);
    }
    this.host.refreshFileViews();await this.host.refreshTree?.();
  }
}
