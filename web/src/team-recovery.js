import {icon,escapeHTML as esc} from './icons.js';

/** Recovery stays in CoCo; it never starts a listener or a program on page load. */
export function mountTeamRecovery(team){
  const root=team.root,recovery=team.state.recovery;
  if(recovery){
    root.querySelector('.team-intro').hidden=true;
    const panel=document.createElement('section');panel.className='coco-recovery';panel.setAttribute('aria-label','Recuperación de CoCo');
    panel.innerHTML=`<div>${icon('clock')}<div><strong>${recovery.error?'Recuperación pendiente de revisión':recovery.guest?'Tu equipo te espera':'Puedes continuar tu sesión compartida'}</strong><p>${esc(recovery.error||(recovery.guest?'Vuelve a conectar con tu identidad y tus permisos.':`${recovery.documents.length} archivos · ${recovery.participants} estaciones registradas. Los cambios compartidos permanecen sin guardar en el proyecto.`))}</p>${recovery.mode==='internet'?'<p>Al recuperar se prepara una dirección HTTPS nueva. Comparte la nueva invitación.</p>':''}</div></div><div class="coco-recovery-actions">${recovery.available?'<button class="primary-button" data-coco-resume>Continuar sesión</button><button class="text-button" data-coco-forget>Descartar recuperación</button>':''}</div>`;
    root.querySelector('.team-intro').before(panel);
    const resume=panel.querySelector('[data-coco-resume]');
    if(resume)resume.onclick=()=>team.host.platform.safe(async()=>{
      resume.disabled=true;
      try{team.state=await team.api('/recover',{});await team.connect();await team.open();}
      finally{resume.disabled=false;}
    });
    const forget=panel.querySelector('[data-coco-forget]');
    if(forget)forget.onclick=()=>team.host.platform.safe(async()=>{
      const confirmed=recovery.guest||await team.host.platform.host.confirmDialog('Descartar la sesión recuperable','Se eliminarán la copia compartida pendiente y su invitación. Los archivos guardados del proyecto se conservarán.','Descartar recuperación');
      if(confirmed)await team.api('/stop',{});
      await team.open();
    });
  }
  const live=document.createElement('section');live.className='coco-recovery';live.dataset.cocoRecovered='';live.hidden=true;
  root.querySelector('[data-team-active]').prepend(live);
  const copies=document.createElement('section');copies.className='coco-recovery';copies.dataset.cocoLocalDrafts='';copies.hidden=true;root.querySelector('header').after(copies);paintLocalDrafts(team);
}

export function paintTeamRecovery(team){
  paintLocalDrafts(team);
  const panel=team.root?.querySelector('[data-coco-recovered]'),recovery=team.snapshot?.recovery;
  if(!panel||!recovery)return;
  const interruptions=recovery.interruptions||[],conflicts=recovery.conflicts||[],pending=recovery.pendingOperations||[];
  panel.hidden=!recovery.restored&&!interruptions.length;
  const signature=JSON.stringify([recovery,team.state.hosting]);if(panel.dataset.signature===signature)return;panel.dataset.signature=signature;
  panel.innerHTML=`<div>${icon('check')}<div><strong>${interruptions.length||conflicts.length||pending.length?'Sesión recuperada · requiere atención':'Sesión recuperada'}</strong><p>Los archivos y permisos se han recuperado. Los programas anteriores no se reinician automáticamente.</p>${conflicts.length?`<p>${conflicts.length===1?'Un archivo cambió':conflicts.length+' archivos cambiaron'} en disco. Se conserva el texto compartido: ${esc(conflicts.slice(0,8).join(', '))}${conflicts.length>8?'…':''}</p>`:''}${pending.length?'<p>Hay operaciones de archivos sin confirmación. Revisa el árbol y los archivos antes de continuar.</p>':''}</div></div><div class="coco-recovery-jobs"></div>`;
  const jobs=panel.querySelector('.coco-recovery-jobs');
  for(const item of interruptions){
    const row=document.createElement('div'),path=Object.entries(team.snapshot.executions||{}).find(([,run])=>run.job===item.job)?.[0]||'Ejecución anterior';
    row.innerHTML=`<span><strong>${esc(path)}</strong><small>${item.processAlive?'El proceso anterior sigue activo; no se ha recuperado su consola.':'Interrumpida o sin resultado confirmado.'}</small></span>`;
    if(team.state.hosting){const button=document.createElement('button');button.className='secondary-button';button.textContent=item.processAlive?'Detener proceso anterior':'Confirmar interrupción';button.onclick=()=>team.host.platform.safe(async()=>{await team.api('/request',{action:'acknowledge-interruption',job:item.job,stop:item.processAlive});await team.sync();});row.append(button);}
    jobs.append(row);
  }
  if(pending.length&&team.state.hosting){const button=document.createElement('button');button.className='secondary-button';button.textContent='He revisado las operaciones pendientes';button.onclick=()=>team.host.platform.safe(async()=>{await team.api('/request',{action:'review-recovery'});await team.sync();});jobs.append(button);}
}

function paintLocalDrafts(team){
  const panel=team.root?.querySelector('[data-coco-local-drafts]');if(!panel)return;
  const drafts=team.state.localDrafts||[];panel.hidden=!drafts.length;const signature=JSON.stringify(drafts);if(panel.dataset.signature===signature)return;panel.dataset.signature=signature;
  panel.innerHTML=`<div>${icon('files')}<div><strong>Borradores locales conservados</strong><p>Estas copias diferían de la sala al recuperar el editor. Puedes revisarlas y copiar el contenido; los archivos y el texto compartido se conservan por separado.</p></div></div><div class="coco-recovery-actions"></div>`;
  for(const draft of drafts){const button=document.createElement('button');button.className='secondary-button';button.textContent='Revisar borrador · '+draft.path;button.onclick=()=>team.host.platform.safe(()=>showLocalDraft(team,draft.id));panel.lastElementChild.append(button);}
}

async function showLocalDraft(team,id){
  const draft=await team.api('/local-draft',{action:'read',id});
  team.host.modal('Borrador local recuperado',`<section class="coco-local-draft"><p>${esc(draft.path)}</p><p>Esta es tu copia local anterior a la sincronización. Revísala y copia las partes que quieras conservar en el archivo compartido.</p><pre>${esc(draft.text)}</pre><div class="modal-actions"><button class="secondary-button" data-coco-draft-back>${icon('chevron-left')}Volver a CoCo</button><button class="primary-button" data-coco-draft-copy>${icon('copy')}Copiar borrador</button><button class="text-button" data-coco-draft-discard>Descartar esta copia</button></div></section>`,{wide:true});
  const root=document.querySelector('.coco-local-draft');root.querySelector('[data-coco-draft-back]').onclick=()=>team.host.platform.safe(()=>team.open());
  root.querySelector('[data-coco-draft-copy]').onclick=()=>team.host.platform.safe(()=>navigator.clipboard.writeText(draft.text));
  root.querySelector('[data-coco-draft-discard]').onclick=()=>team.host.platform.safe(async()=>{const confirmed=await team.host.platform.host.confirmDialog('Descartar copia local','Se eliminará únicamente este borrador de recuperación. Los archivos guardados y la sala compartida se conservarán.','Descartar copia');if(confirmed){await team.api('/local-draft',{action:'discard',id});await team.open();}else await showLocalDraft(team,id);});
}
