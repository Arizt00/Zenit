import {icon,escapeHTML as esc} from './icons.js';
import {languageFor,languageLabel} from './editor.js';
import {ReviewedEdits} from './reviewed-edits.js';
import {showExecutionReadiness} from './execution-readiness.js';
import {GitWorkbenchUI} from './git-workbench.js';
import {NavigationHistory} from './navigation-state.js';
import {showLanguageVerification} from './language-verification.js';

export class EditorDepth{
 constructor(h){
  this.h=h;this.workspace=h.service().workspace;this.navigation=new NavigationHistory();this.edits=new ReviewedEdits(h);h.platform.reviewedEdits=this.edits;h.platform.editorDepth=this;this.git=new GitWorkbenchUI(h);
  h.commands.push(['editor-back','chevron-left','Navegación: volver atrás','Alt Left'],['editor-forward','chevron-right','Navegación: ir adelante','Alt Right'],['editor-symbols','code','Navegación: símbolos del archivo','Ctrl Shift O'],['editor-language-capabilities','code','Lenguaje: funciones disponibles en este archivo',''],['editor-undo-review','undo','Deshacer conjunto revisado',''],['editor-replace-project','search','Buscar y reemplazar en el proyecto','Ctrl Shift H'],['git-workbench','git','Git: revisar y preparar cambios locales','']);
  h.commands.push(['language-verification','check','Lenguajes: comprobar recorridos y referencia nC','']);
  const handle=h.desktop.handle.bind(h.desktop);h.desktop.handle=async(action,...args)=>{
   if(action==='language-verification'){await showLanguageVerification(h);return true;}
   if(action==='editor-back'||action==='editor-forward'){await this.move(action==='editor-back'?-1:1);return true;}
   if(action==='editor-language-capabilities'){this.capabilities();return true;}
   if(action==='editor-undo-review'){await this.edits.undo();return true;}
   if(action==='editor-symbols'){this.beforeJump();h.editor.view.focus();await h.editor.view.getAction('editor.action.quickOutline')?.run();this.afterJump();return true;}
   if(action==='editor-replace-project'){h.studio.search();document.querySelector('[data-search-show-replace]')?.click();return true;}
   if(action==='git-workbench'){await this.git.open();return true;}
   return handle(action,...args);
  };
  const node=document.createElement('div');node.className='editor-depth-controls';node.innerHTML=`<button class="icon-button" data-nav-back aria-label="Volver atrás (Alt+Izquierda)" title="Volver atrás (Alt+Izquierda)">${icon('chevron-left')}</button><button class="icon-button" data-nav-forward aria-label="Ir adelante (Alt+Derecha)" title="Ir adelante (Alt+Derecha)">${icon('chevron-right')}</button><button class="icon-button" data-language-capabilities aria-label="Funciones del lenguaje actual" title="Funciones del lenguaje actual">${icon('code')}</button>`;this.controls=node;document.querySelector('.editor-tabbar .new-tab').after(node);
  node.querySelector('[data-nav-back]').onclick=()=>h.platform.safe(()=>this.move(-1));node.querySelector('[data-nav-forward]').onclick=()=>h.platform.safe(()=>this.move(1));node.querySelector('[data-language-capabilities]').onclick=()=>this.capabilities();
  const ed=h.editor,activate=ed.activate.bind(ed);this.originalActivate=activate;
  ed.activate=path=>{if(!this.replaying)this.remember();const result=activate(path);if(!this.replaying)this.remember();this.update();return result;};
  this.key=e=>{const key=e.key.toLowerCase(),direction=key==='y'||key==='z'&&e.shiftKey?'redo':'undo';if((e.ctrlKey||e.metaKey)&&!e.altKey&&['z','y'].includes(key)&&ed.view?.hasTextFocus()&&this.edits.canRestore(direction)&&this.edits.last.rows.some(r=>r.model===ed.view.getModel())){e.preventDefault();e.stopImmediatePropagation();h.platform.safe(()=>this.edits[direction]());return;}if(e.altKey&&!e.ctrlKey&&['ArrowLeft','ArrowRight'].includes(e.key)&&ed.view?.hasTextFocus()){e.preventDefault();e.stopImmediatePropagation();h.platform.safe(()=>this.move(e.key==='ArrowLeft'?-1:1));}if((e.ctrlKey||e.metaKey)&&e.shiftKey&&!e.altKey){const key=e.key.toLowerCase();if(key==='h'||key==='o'&&ed.view?.hasTextFocus()){e.preventDefault();e.stopImmediatePropagation();h.platform.safe(()=>h.desktop.handle(key==='h'?'editor-replace-project':'editor-symbols'));}}};
  window.addEventListener('keydown',this.key,true);
  this.renamed=e=>{for(const row of this.navigation.rows){const move=e.detail.find(r=>row.path===r.oldPath||row.path.startsWith(r.oldPath+'/'));if(move)row.path=move.path+row.path.slice(move.oldPath.length);}this.update();};document.addEventListener('zenit:files-renamed',this.renamed);
  this.deleted=e=>{this.navigation.removePaths(e.detail);this.update();};document.addEventListener('zenit:files-deleted',this.deleted);
  window.addEventListener('pagehide',()=>{window.removeEventListener('keydown',this.key,true);document.removeEventListener('zenit:files-renamed',this.renamed);document.removeEventListener('zenit:files-deleted',this.deleted);this.git.dispose();},{once:true});
  this.remember();this.update();
  const m=window.monaco;
  this.reviewCommand=m?.editor.registerCommand('zenit.reviewed.edit',async(_,edit,path,version,command,args,title)=>{
   try{const model=ed.models.get(path)?.model;if(!model||model.getVersionId()!==version)throw Error('La acción caducó. Solicítala de nuevo.');const changes=await this.edits.workspaceChanges(edit,model,version);if(await this.edits.apply(changes,{title:title||'Revisar acción de código'}))if(command)await h.platform.pluginCommand(command,args);}
   catch(error){h.notify(error.message,'error');}
  });
  this.languageCommand=m?.editor.registerCommand('zenit.language.review',async(_,id,action,path,version)=>{
   try{
    const p=h.platform,s=p.lspSessions.get(id),model=ed.models.get(path)?.model;if(!s||!model||model.getVersionId()!==version)throw Error('La acción caducó. Solicítala de nuevo.');
    if(action.data&&s.capabilities.codeActionProvider?.resolveProvider)action=(await p.api('/lsp/request',{id,method:'codeAction/resolve',params:action})).result;
    let accepted=true;if(action.edit){const changes=await this.edits.workspaceChanges(action.edit,model,version);accepted=await this.edits.apply(changes,{title:action.title});}
    const command=typeof action.command==='string'?action.command:action.command?.command,args=action.arguments||action.command?.arguments||[];
    if(accepted&&command){await p.syncLSP(s);await p.api('/lsp/request',{id,method:'workspace/executeCommand',params:{command,arguments:args}});}
   }catch(error){h.notify(error.message,'error');}
  });
 }
 location(){const ed=this.h.editor,pos=ed.view?.getPosition()||{lineNumber:1,column:1};return {path:ed.current,line:pos.lineNumber,column:pos.column};}
 remember(){if(this.workspace!==this.h.service().workspace){this.workspace=this.h.service().workspace;this.navigation=new NavigationHistory();}this.navigation.push(this.location());}
 beforeJump(){this.remember();this.jumpAnchor=this.navigation.index;}
 afterJump(){const at=this.location();if(this.navigation.index>this.jumpAnchor)this.navigation.replace(at);else this.navigation.push(at);this.update();}
 update(){const path=this.h.editor.current,back=this.controls.querySelector('[data-nav-back]'),forward=this.controls.querySelector('[data-nav-forward]'),language=this.controls.querySelector('[data-language-capabilities]');back.disabled=this.navigation.index<=0;forward.disabled=this.navigation.index>=this.navigation.rows.length-1;back.hidden=back.disabled&&forward.disabled;forward.hidden=forward.disabled;this.controls.hidden=!path;language.classList.add('editor-language-chip');const label=languageLabel(path||'');language.innerHTML=icon('code')+'<span>'+esc(label)+'</span>';language.setAttribute('aria-label','Funciones de '+label+' para '+path);language.title='Funciones de '+label;}
 async move(direction){
  if(this.workspace!==this.h.service().workspace){this.remember();this.update();return;}
  this.navigation.replace(this.location());const previous=this.navigation.index,target=this.navigation.move(direction);if(!target)return;this.replaying=true;
  try{await this.h.openFile(target.path);const view=this.h.editor.view;if(view?.getModel()){view.setPosition({lineNumber:target.line,column:target.column});view.revealPositionInCenter(view.getPosition());view.focus();}}
  catch(error){this.navigation.index=previous;throw error;}finally{this.replaying=false;this.update();}
 }
 buffers(){return [...this.h.editor.models].filter(([path,r])=>r.model&&this.h.editor.isDirty(path)&&!r.transient&&!/^(?:[A-Za-z]:|\/)/.test(path)).map(([path,r])=>({path,content:r.model.getValue(),revision:r.revision}));}
 async replace(state){
  if(state.mode!=='content')throw Error('Selecciona Contenido para reemplazar texto.');if(!await this.h.platform.host.ensureTrust())return;
  const workspace=this.h.service().workspace,plan=await this.h.platform.api('/editor/replace/preview',{...state,query:state.query,replacement:document.querySelector('[data-search-replacement]').value,buffers:this.buffers()});
  if(workspace!==this.h.service().workspace)return;
  if(plan.limited)throw Error('La revisión alcanzó su límite de archivos o coincidencias. Reduce los filtros y vuelve a revisar.');
  if(plan.skipped)this.h.notify(plan.skipped+' archivos no pudieron revisarse por tamaño o codificación.','info');
  await this.edits.apply(plan.files,{title:'Revisar reemplazo · '+plan.occurrences+' coincidencias',verify:()=>this.h.platform.api('/editor/replace/verify',{plan:plan.id})});
 }
 can(kind){
  const lang=languageFor(this.h.editor.current),flags={definition:'definitionProvider',declaration:'declarationProvider',references:'referencesProvider',implementation:'implementationProvider',typeDefinition:'typeDefinitionProvider'};
  return [...this.h.platform.lspSessions.values()].some(s=>s.languages.includes(lang)&&s.capabilities[flags[kind]])||(this.h.preview.runtimeHosts||[]).some(host=>host.running&&(host.providers||[]).some(p=>p.language===lang&&p.kind===kind));
 }
 capabilities(){
  const p=this.h.platform,ed=this.h.editor,path=ed.current;if(!path)return this.h.notify('Abre un archivo para revisar su lenguaje.');const lang=languageFor(path),sources=[];
  for(const host of this.h.preview.runtimeHosts||[])if(host.running){const kinds=[...new Set((host.providers||[]).filter(r=>r.language===lang).map(r=>r.kind))];if(kinds.length)sources.push({label:this.h.preview.extensionMetadata?.get(host.id)?.displayName||host.id,kinds});}
  const flags={completionProvider:'completion',definitionProvider:'definition',referencesProvider:'references',documentSymbolProvider:'symbols',renameProvider:'rename',codeActionProvider:'actions',documentFormattingProvider:'format',implementationProvider:'implementation',typeDefinitionProvider:'typeDefinition',foldingRangeProvider:'folding',hoverProvider:'hover',semanticTokensProvider:'semantic'};
  for(const s of p.lspSessions.values())if(s.languages.includes(lang))sources.push({label:s.profile||s.id,kinds:Object.entries(flags).filter(([flag])=>s.capabilities[flag]).map(([,kind])=>kind)});
  const labels={completion:'Autocompletado',definition:'Definición',references:'Referencias',symbols:'Símbolos',rename:'Renombrado',actions:'Acciones de código',format:'Formato',implementation:'Implementaciones',typeDefinition:'Definición de tipos',folding:'Plegado',hover:'Documentación',semantic:'Colores semánticos',diagnostics:'Diagnósticos',codelens:'CodeLens',inlay:'Pistas en línea',onTypeFormat:'Formato al escribir'};
  this.h.modal('Funciones del lenguaje',`<section class="language-depth-report"><header>${icon('code')}<div><strong>${esc(languageLabel(path))}</strong><small>${esc(path)}</small></div></header><p>Funciones anunciadas por los servicios activos para este archivo. El compilador y el depurador se comprueban por separado.</p>${sources.map(s=>`<article><h4>${esc(s.label)}</h4><div>${s.kinds.map(k=>`<span>${icon('check')}${esc(labels[k]||k)}</span>`).join('')}</div></article>`).join('')||'<p>No hay un servidor o extensión activo que anuncie funciones semánticas para este lenguaje. La edición y la búsqueda de texto siguen disponibles.</p>'}<div class="modal-actions"><button class="secondary-button" data-depth-tools>${icon('build')}Comprobar herramientas y destino</button><button class="primary-button" data-depth-symbols>${icon('code')}Símbolos del archivo</button></div></section>`);
  const verify=document.createElement('button');verify.className='secondary-button';verify.innerHTML=icon('check')+'Recorridos comprobables';verify.onclick=()=>p.safe(()=>showLanguageVerification(this.h));document.querySelector('.language-depth-report .modal-actions').prepend(verify);
  document.querySelector('[data-depth-tools]').onclick=()=>p.safe(()=>showExecutionReadiness(this.h));document.querySelector('[data-depth-symbols]').onclick=()=>{this.h.closeModal();p.safe(()=>this.h.desktop.handle('editor-symbols'));};
 }
}
