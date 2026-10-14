import {icon,escapeHTML as esc} from './icons.js';
import {lanternRevisions,compareLanternOutput} from './lantern-evidence.js';
export function renderLanternReview(view,root){
  if(!root.matches('.lantern-workbench'))return;
  const t=(es,en)=>view.studio.t(es,en),s=view.state,revisions=lanternRevisions(s);
  let shell=root.querySelector('.lantern-review');
  if(!shell){
    shell=document.createElement('section');shell.className='lantern-review';
    shell.innerHTML=`<div class="lantern-follow"><button type="button" data-lantern="pin">${icon('file')}<span></span></button><small></small></div><details><summary><span></span><small></small></summary><div class="lantern-revision-list"></div><div class="lantern-comparison" hidden></div></details>`;
    root.querySelector('.lantern-output').before(shell);
    shell.onclick=e=>{const button=e.target.closest('[data-baseline]');if(!button)return;view.baselineRevision=+button.dataset.baseline;renderLanternReview(view,root);};
    shell.querySelector('details').ontoggle=()=>renderLanternReview(view,root);
  }
  const pinned=view.host.platform.prefs['lantern.followActive']===false;
  shell.querySelector('[data-lantern=pin] span').textContent=t(pinned?'Archivo fijado':'Seguir archivo activo',pinned?'File pinned':'Follow active file');shell.querySelector('[data-lantern=pin]').setAttribute('aria-pressed',String(pinned));
  shell.querySelector('.lantern-follow>small').textContent=t(pinned?'Cambiar de pestaña conserva esta sesión.':'La sesión cambia con el editor.',pinned?'Switching tabs keeps this session.':'The session follows the editor.');
  shell.querySelector('summary span').textContent=t('Revisiones de ejecución','Execution revisions');shell.querySelector('summary small').textContent=String(revisions.length);
  const list=shell.querySelector('.lantern-revision-list'),baseline=revisions.find(x=>x.revision===view.baselineRevision)||revisions.at(-2),latest=revisions.at(-1);
  list.innerHTML=revisions.length?revisions.slice(-8).map(r=>`<button type="button" data-baseline="${r.revision}" aria-pressed="${r===baseline}" ${r===latest?'disabled':''}><strong>R${r.revision}</strong><small>${r.code==null?t('En curso','Running'):t('Salida ','Exit ')+r.code}</small>${r===latest?`<span>${t('Actual','Current')}</span>`:''}</button>`).join(''):`<p>${t('Las revisiones aparecerán después de ejecutar.','Revisions appear after execution.')}</p>`;
  const output=shell.querySelector('.lantern-comparison');output.hidden=!baseline||!latest||baseline===latest;
  if(!shell.querySelector('details').open){output.replaceChildren();return;}
  if(!output.hidden){const diff=compareLanternOutput(baseline.output,latest.output);output.innerHTML=`<header><strong>R${baseline.revision} → R${latest.revision}</strong><small>+${diff.added} −${diff.removed}${diff.truncated?' · '+t('Comparación limitada','Bounded comparison'):''}</small></header><pre tabindex="0">${diff.lines.map(x=>`<span class="output-${x.kind}">${x.kind==='added'?'+':x.kind==='removed'?'−':' '} ${esc(x.text)}</span>`).join('\n')}</pre>`;}
}
