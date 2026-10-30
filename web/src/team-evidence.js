import {icon,escapeHTML as esc} from './icons.js';

export async function showTeamEvidence(team){
  const entry=team.files.get(team.host.editor.current),execution=team.snapshot?.executions?.[entry?.path];
  if(!execution)throw Error('Ejecuta primero este archivo en el anfitrión para consultar su origen.');
  const record=await team.api('/request',{action:'evidence',job:execution.job});
  const state=(record.interrupted?'Ejecución interrumpida. ':'')+(record.sourceMatches&&record.environmentMatches&&record.toolsMatch&&record.contextVerification?.status!=='changed'?'Coincide con el archivo, el búfer y la configuración actuales':'El archivo, el búfer o la configuración cambiaron después de iniciar');
  const resultLabel=record.interrupted?'Interrumpida · resultado sin confirmar':record.done?'Finalizada · código '+String(record.code):'En curso';
  team.host.modal('Origen de la ejecución',`<section class="team-evidence"><header><h3>${esc(record.path)}</h3><p>${esc(state)}</p></header><dl><dt>Revisión del archivo</dt><dd><code>${esc(record.sourceSha256)}</code></dd><dt>Entorno reconstruido</dt><dd>${esc(record.environment.environmentId||'Sin reconstrucción portátil verificada')}</dd><dt>Resultado</dt><dd>${esc(resultLabel)}</dd></dl><h4>Órdenes en el anfitrión</h4><pre>${esc(record.commands.map(c=>Array.isArray(c)?c.map(a=>JSON.stringify(a)).join(' '):c).join('\n'))}</pre><p class="lab-note">${esc(record.scope)}</p><div class="modal-actions"><button class="secondary-button" data-origin-back>${icon('chevron-left')}Volver a CoCo</button><button class="primary-button" data-origin-melody>${icon('sparkles')}Explicar con Melody</button></div></section>`,{wide:true});
  const root=document.querySelector('.team-evidence');root.querySelector('[data-origin-back]').onclick=()=>team.host.platform.safe(()=>team.open());
  root.querySelector('[data-origin-melody]').onclick=()=>team.host.platform.safe(async()=>{
    const question='Explica esta evidencia de una ejecución compartida. Distingue los hechos registrados de tus inferencias y las limitaciones de su alcance. No afirmes que ejecutaste el programa ni que sus dependencias externas se congelaron.\n'+JSON.stringify(record);
    team.host.closeModal();team.host.platform.host.studio.host.dock.show('assistant');team.host.platform.setMelodyMode?.('chat');document.getElementById('ai-input').value=question;await team.host.platform.sendAI(question,{consult:true});
  });
}
