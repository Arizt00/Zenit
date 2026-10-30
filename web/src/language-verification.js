import {icon,escapeHTML as esc} from './icons.js';

const steps={project:'Abrir proyecto',navigation:'Ir a definición',rename:'Renombrar',build:'Compilar y ejecutar',test:'Pruebas o humo',debug:'Pausa y paso'};
const statuses={passed:'Comprobado',failed:'Fallo observado',missing:'Falta una integración o herramienta','not-tested':'Sin comprobar'};
const modes={native:'Nativo',adapted:'Adaptado',missing:'Falta'};
export function journeySummary(report,stale){
 if(!report)return 'Sin recorrido ejecutado';
 if(stale||report.stale)return 'Resultado anterior · repite tras cambiar herramientas o extensiones';
 return report.steps.filter(s=>s.status==='passed').length+' de '+Object.keys(steps).length+' pasos comprobados';
}
export async function showLanguageVerification(h){
 const p=h.platform,workspace=h.service().workspace,data=await p.api('/languages/verification');if(workspace!==h.service().workspace)return;
 h.modal('Recorridos de lenguajes',`<section class="language-depth-report language-verification"><header>${icon('code')}<div><strong>Capacidades con evidencia</strong><small>${esc(data.scope)}</small></div></header><p>La comprobación usa una muestra temporal, las herramientas de Este equipo y los perfiles estándar de Zénit. Puede compilar, iniciar la extensión nC habilitada y arrancar depuradores. Los comandos personalizados no se ejecutan. No modifica tus archivos, no instala paquetes y no certifica servicios que sólo anuncian una capacidad.</p><div class="language-journeys">${data.languages.map(row=>`<article><h4>${esc(row.label)}</h4><p>${esc(journeySummary(row.report,row.stale))}</p>${row.report?`<small>${esc(new Date(row.report.checkedAt*1000).toLocaleString())} · muestra ${esc(row.report.fixtureSha256?.slice(0,12)||'sin preparar')}</small><details class="journey-steps"><summary>Ver los seis pasos</summary><dl>${row.report.steps.map(s=>`<div><dt>${esc(steps[s.id])}</dt><dd><strong data-status="${esc(s.status)}">${esc(statuses[s.status]||s.status)}</strong><details><summary>Ver evidencia · ${Math.round(s.durationMs)} ms</summary><pre>${esc(s.detail)}</pre></details></dd></div>`).join('')}</dl></details>`:'<p class="muted-copy">Herramientas detectadas y pruebas de comportamiento son comprobaciones distintas.</p>'}<button class="secondary-button" data-journey="${esc(row.id)}">${icon('play')}Comprobar muestra</button></article>`).join('')}</div><details class="nc-reference"><summary>nC · plugin ${esc(data.nc.version)} · nativo, adaptado y pendiente</summary><p>${esc(data.nc.notice)}</p><p>${esc(data.nc.filename)} · SHA-256 <code>${esc(data.nc.sha256)}</code></p>${data.nc.installed.map(i=>`<p>${icon(i.matchesReference?'check':'alert')} ${esc(i.id)} ${esc(i.version)} · ${i.matchesReference?'Procedencia coincidente':'Procedencia diferente'} · ${i.enabled?'habilitado':'deshabilitado'}</p>`).join('')||'<p>No se ha localizado el paquete adaptado en este perfil.</p>'}<table><thead><tr><th>Declaración original</th><th>Equivalente</th><th>Integración</th></tr></thead><tbody>${[...data.nc.declarations,...data.nc.actions.map(a=>({...a,point:a.text||a.id}))].map(d=>`<tr><td>${esc(d.name||d.point)}${d.extensions?' · .'+esc(d.extensions):''}</td><td>${esc(d.route)}</td><td>${esc(modes[d.mode])}</td></tr>`).join('')}</tbody></table><p>Los recorridos anteriores comprueban su muestra. Colores, iconos, pistas y autoimportación necesitan sus propias pruebas visuales o de comportamiento; no se deducen de esta tabla.</p></details><p data-journey-state role="status"></p><div class="modal-actions"><button class="secondary-button" data-journey-refresh>${icon('refresh')}Actualizar resultados</button></div></section>`,{wide:true});
 document.querySelector('[data-journey-refresh]').onclick=()=>p.safe(()=>showLanguageVerification(h));
 document.querySelectorAll('[data-journey]').forEach(button=>button.onclick=()=>p.safe(async()=>{
  if(!await p.host.ensureTrust())return;
  const node=document.querySelector('[data-journey-state]');document.querySelectorAll('[data-journey]').forEach(b=>b.disabled=true);node.textContent='Comprobando muestra local…';
  try{
   const task=await p.api('/languages/verification/run',{language:button.dataset.journey,consent:true});node.innerHTML=`Comprobando muestra local. <button class="text-button" data-journey-cancel>Cancelar</button>`;node.querySelector('button').onclick=()=>p.safe(()=>p.api('/operations/cancel',{id:task.job}));
   while(node.isConnected&&workspace===h.service().workspace){
    const state=await p.api('/operations'),job=state.jobs.find(j=>j.id===task.job);if(!job)throw Error('La comprobación ya no pertenece a este proyecto.');
    if(job.state==='done'){await showLanguageVerification(h);return;}
    if(['failed','cancelled'].includes(job.state))throw Error(job.error||'Comprobación cancelada.');
    await new Promise(resolve=>setTimeout(resolve,500));
   }
  }catch(error){if(node.isConnected)node.textContent=error.message;}
  finally{if(node.isConnected)document.querySelectorAll('[data-journey]').forEach(b=>b.disabled=false);}
 }));
}
