import {icon,escapeHTML as esc} from './icons.js';
const TOOLS=[['capsule','cube','Evidence capsule','Freeze the unsaved source, diagnostics and execution evidence.'],['drift','split','Drift lens','Compare this buffer with its latest frozen capsule.'],['impact','git','Reference weave','Find static source relations with their exact evidence lines.'],['faults','bug','Fault atlas','Group recurring diagnostics and execution signals.'],['handoff','files','Handoff brief','Create a portable session brief from observed facts.']];
function presentation(result){
  if(result.tool==='capsule')return `<div class="research-facts"><div><small>Capture</small><strong>Unsaved buffer</strong></div><div><small>Local history</small><strong>${result.stored} / 12 capsules</strong></div><div><small>Source fingerprint</small><code>${esc(result.sha256.slice(0,16))}</code></div></div><p class="research-note">Freeze again before a risky change. Drift lens compares future edits with this exact source.</p>`;
  if(result.tool==='drift')return `<p class="research-note">${result.changed?'Source changed since capture.':'Source matches the capsule.'}${result.truncated?' The diff is truncated.':''}</p><pre tabindex="0">${(result.diff||'No source changes.').split('\n').map(line=>`<span class="${line.startsWith('+')?'diff-added':line.startsWith('-')?'diff-removed':line.startsWith('@@')?'diff-hunk':''}">${esc(line)}</span>`).join('\n')}</pre>`;
  if(result.tool==='impact')return `<p class="research-note">${result.scanned} files scanned${result.truncated?' · bounded scan':''}</p><div class="research-evidence-list">${result.relations.map(r=>`<button data-evidence-path="${esc(r.path)}" data-evidence-line="${r.line}"><strong>${esc(r.path)}:${r.line}</strong><code>${esc(r.reference)}</code><small>${esc(r.kind)}</small></button>`).join('')||'<p>No static references found within the scan boundary.</p>'}</div>`;
  if(result.tool==='faults')return `<div class="research-evidence-list">${result.groups.map(g=>`<article><h4>${esc(g.signature)}</h4>${g.evidence.map(d=>`<p><strong>${esc(d.severity||'Diagnostic')}</strong> · ${esc(d.path)}:${esc(d.line)}<br>${esc(d.message)}</p>`).join('')}</article>`).join('')||'<p>No editor diagnostics supplied.</p>'}${result.outputSignals.length?'<article><h4>Execution signals</h4><pre>'+esc(result.outputSignals.join('\n'))+'</pre></article>':''}</div>`;
  return `<label class="handoff-editor">Add your intent or next verification<textarea aria-label="Session handoff brief">${esc(result.brief)}</textarea></label>`;
}
export function installMelodyResearch(host){
  const p=host.platform,h=p.host,ed=h.editor;
  const tools=document.createElement('details');tools.className='melody-research';tools.innerHTML=`<summary>${icon('flask')}Evidence tools<span>5</span></summary><div>${TOOLS.map(([id,glyph,name,hint])=>`<button type="button" data-research="${id}" title="${hint}">${icon(glyph)}<span>${name}</span></button>`).join('')}</div>`;
  document.querySelector('.melody-context-actions').before(tools);
  tools.onclick=e=>{const button=e.target.closest('[data-research]');if(!button)return;p.safe(async()=>{
    const path=ed.current;if(!path||ed.models.get(path)?.kind==='binary')throw Error('Open a project text file first.');
    button.disabled=true;
    try{
      const diagnostics=[...p.diagnosticMap].flatMap(([file,items])=>items.map(item=>({...item,path:file}))).slice(0,500);
      const debug=await p.api('/debug'),terminal=p.terminals.get(p.activeTerminal),buffer=terminal?.xterm?.buffer?.active;
      const output=buffer?Array.from({length:Math.min(80,buffer.length)},(_,i)=>buffer.getLine(Math.max(0,buffer.length-80)+i)?.translateToString(true)||'').join('\n'):debug.output||'';
      const result=await p.api('/melody/research',{action:button.dataset.research,path,content:ed.getValue(),diagnostics,output});
      const title=TOOLS.find(x=>x[0]===button.dataset.research)[2];const text=result.brief||result.diff||JSON.stringify(result,null,2);
      h.modal(title,`<div class="research-result"><p>${esc(result.summary)}</p><small>Local evidence · ${esc(path)} · ${esc(result.sha256.slice(0,12))}</small>${presentation(result)}<div class="modal-actions"><button class="secondary-button" data-research-copy>${icon('copy')}Copy evidence</button><button class="primary-button" data-research-ask>${icon('sparkles')}Ask Melody</button></div></div>`,{wide:true});
      const evidence=()=>document.querySelector('.handoff-editor textarea')?.value||text;
      document.querySelector('[data-research-copy]').onclick=()=>p.safe(async()=>{await navigator.clipboard.writeText(evidence());h.notify('Evidence copied.');});
      document.querySelectorAll('[data-evidence-path]').forEach(b=>b.onclick=()=>p.safe(async()=>{h.closeModal();await h.openFile(b.dataset.evidencePath,+b.dataset.evidenceLine);}));
      document.querySelector('[data-research-ask]').onclick=()=>p.safe(async()=>{const context=evidence();h.closeModal();h.dock.floatPanel('assistant');p.melodyMode='chat';const question='Review this '+title+' using only the supplied evidence. Separate facts, missing evidence, and hypotheses. Propose the next verification. Do not edit files.\n'+context;document.getElementById('ai-input').value=question;if(!p.prefs['ai.model'])return p.settings('ai');await p.sendAI(question,{consult:true});});
    }finally{button.disabled=false;}
  });};
}
