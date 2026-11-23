import {icon,escapeHTML as esc} from './icons.js';

/** Run evidence first; consulting the model remains a separate, reviewable action. */
export function installCountercheck(p){
 const h=p.host,ed=h.editor,results=new Map();
 p.openCountercheck=async()=>{
  const path=ed.current,workspace=h.workspace(),record=ed.models.get(path);
  if(!record||record.kind==='binary')throw Error('Abre un archivo de código para preparar Contraprueba.');
  if(!await h.ensureTrust())return;
  const content=record.model?.getValue()??record.value;
  h.modal('Melody · Contraprueba',`<form class="countercheck-form"><p>Compara <strong>${esc(path)}</strong> guardado con su búfer actual, con la misma entrada y sin sustituir las fuentes.</p><label>Entrada para ambas variantes<textarea name="stdin" rows="3" maxlength="16384" placeholder="Opcional · se cierra la entrada después de enviarla"></textarea></label><label>Límite por variante<select name="timeout"><option value="5">5 segundos</option><option value="10" selected>10 segundos</option><option value="30">30 segundos</option><option value="60">60 segundos</option></select></label><div class="modal-actions"><button class="primary-button">${icon('flask')}Revisar Contraprueba</button></div></form>`,{wide:true});
  document.querySelector('.countercheck-form').onsubmit=e=>{e.preventDefault();p.safe(async()=>{
   const form=new FormData(e.target);const plan=await p.api('/melody/countercheck/plan',{path,content,stdin:form.get('stdin'),timeout:Number(form.get('timeout'))});
   h.modal('Revisar Contraprueba',`<section class="countercheck-review"><div class="evidence-heading">${icon('flask')}<div><strong>${esc(path)}</strong><small>Guardado → búfer · ${plan.inputBytes} bytes de entrada · ${plan.timeout} s por variante</small></div></div><p>${esc(plan.notice)}</p>${plan.same?'<p class="countercheck-note">Ambas variantes tienen el mismo contenido. Puedes comprobar si su salida se mantiene.</p>':`<details><summary>Diferencias del código</summary><pre>${esc(plan.diff)}</pre></details>`}<div class="modal-actions"><button class="primary-button" data-countercheck-run>${icon('play')}Ejecutar ambas variantes</button></div></section>`,{wide:true});
   document.querySelector('[data-countercheck-run]').onclick=()=>p.safe(async()=>{
    const task=await p.api('/melody/countercheck/run',{plan:plan.id});
    h.modal('Contraprueba en curso',`<section class="countercheck-progress" role="status"><span class="task-spinner"></span><strong>Dos variantes, una ejecución a la vez</strong><p data-countercheck-stage>Preparando las copias…</p><button class="secondary-button" data-countercheck-cancel>${icon('stop')}Cancelar</button><small>Puedes seguir editando. El resultado corresponde al búfer revisado.</small></section>`);
    const cancel=document.querySelector('[data-countercheck-cancel]');cancel.onclick=()=>p.safe(async()=>{await p.api('/operations/cancel',{id:task.job});cancel.disabled=true;});
    while(!p.disposed){
     const state=await p.api('/operations'),job=state.jobs.find(x=>x.id===task.job);
     if(!job)throw Error('La tarea ya no está disponible en el centro de tareas.');
     const stage=document.querySelector('[data-countercheck-stage]');if(stage)stage.textContent=job.stage;
     if(job.state==='done'){results.set(workspace,job.result);if(h.workspace()===workspace)show(job.result);return;}
     if(['failed','cancelled'].includes(job.state))throw Error(job.error||'Contraprueba cancelada.');
     await new Promise(resolve=>setTimeout(resolve,250));
    }
   });
  });};
 };
 const show=result=>{
  h.modal('Resultado de Contraprueba',`<section class="countercheck-report"><div class="evidence-heading">${icon(result.equivalent?'check':'split')}<div><strong>${result.equivalent?'Misma salida y código de salida':'Las variantes difieren o no terminaron'}</strong><small>${esc(result.path)} · ${result.contextFiles} archivos en el contexto copiado</small></div></div><div class="countercheck-columns">${result.results.map(r=>`<article><header><strong>${r.variant==='saved'?'Guardado':'Búfer'}</strong><small>${r.code===null?'No ejecutado':'Salida '+r.code}${r.elapsedMs!==undefined?' · '+r.elapsedMs+' ms':''}</small></header><pre>${esc(r.error||r.output||'(sin salida)')}</pre>${r.outputTruncated?'<p class="countercheck-note">Extracto final · '+r.outputBytes+' bytes capturados. La comparación utiliza la huella completa.</p>':''}${r.outputComplete===false?'<p class="countercheck-note">La captura no recibió el fin de la salida; no se declara equivalencia.</p>':''}<details><summary>Órdenes y registro</summary><pre>${esc(r.log||r.error||'')}</pre></details></article>`).join('')}</div>${result.outputDiff?`<details><summary>Diferencias de salida</summary><pre>${esc(result.outputDiff)}</pre></details>`:''}<p class="muted-copy">El resultado corresponde a las huellas del código revisado. Los tiempos son observaciones de esta ejecución, no una prueba de rendimiento.</p><div class="modal-actions"><button class="secondary-button" data-countercheck-copy>${icon('copy')}Copiar evidencia</button><button class="primary-button" data-countercheck-ask>${icon('sparkles')}Preparar consulta a Melody</button></div></section>`,{wide:true});
  document.querySelector('[data-countercheck-copy]').onclick=()=>p.safe(()=>navigator.clipboard.writeText(JSON.stringify(result,null,2)));
  document.querySelector('[data-countercheck-ask]').onclick=()=>{h.closeModal();h.dock.show('assistant');p.setMelodyMode?.('chat');const input=document.querySelector('#ai-input'),compact={...result,outputDiff:result.outputDiff.slice(0,2500),results:result.results.map(r=>({...r,output:r.output.slice(0,2500),log:r.log?.slice(0,1500)}))};input.value='Analiza esta Contraprueba. Distingue los resultados observados de las hipótesis. No afirmes que el búfer actual coincide con las huellas sin comprobarlo. Propón una corrección revisable y la siguiente prueba. Los registros de esta consulta pueden estar abreviados.\n'+JSON.stringify(compact,null,2);input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();};
 };
 return {dispose(){delete p.openCountercheck;results.clear();}};
}
