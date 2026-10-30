import {escapeHTML as esc} from './icons.js';

export function evidenceLabel(run){
 if(!run)return 'Sin evidencia';
 if(run.currentEvidence)return 'Contexto revisado';
 if(!run.matchesBuffer)return 'Código modificado';
 if(run.matchesTarget===false)return 'Otro destino';
 if(run.matchesEnvironment===false)return 'Otro entorno';
 if(run.matchesConfiguration===false)return 'Configuración modificada';
 if(run.contextVerification?.status==='changed')return 'Dependencias modificadas';
 if(run.cancelled)return 'Ejecución cancelada';
 if(!(run.complete??run.outputComplete))return 'Ejecución incompleta';
 return 'Contexto sin verificar';
}

export function renderExecutionEvidence(run){
 if(!run)return '';
 const context=run.contextVerification;
 const commands=run.commands||[],hash=run.bufferSha256||run.sourceSha256||'';
 return `<details class="execution-evidence"><summary>Origen y vigencia del resultado</summary><dl><div><dt>Estado</dt><dd>${esc(evidenceLabel(run))}</dd></div><div><dt>Destino observado</dt><dd>${esc(run.target?.label||'No registrado')}</dd></div><div><dt>Entorno</dt><dd>${esc(run.environment||'Sin entorno virtual registrado')}</dd></div><div><dt>Huella del código</dt><dd><code title="${esc(hash)}">${esc(hash?hash.slice(0,20)+'…':'No registrada')}</code></dd></div></dl><p>${esc(context?.notice||'Vuelve a ejecutar para registrar el contexto.')}</p>${context?.changed?.length?`<ul>${context.changed.map(path=>`<li><code>${esc(path)}</code></li>`).join('')}</ul>`:''}<p class="muted-copy">${esc(context?.scope||'')}</p><details class="execution-commands"><summary>Órdenes registradas · ${commands.length}</summary><pre>${esc(commands.map(argv=>typeof argv==='string'?argv:JSON.stringify(argv)).join('\n')||'No registradas en esta revisión')}</pre></details></details>`;
}
