import {editingProvider} from './extension-editing.js';
import {explorerDecorations} from './extension-decorations.js';
import {icon,escapeHTML as esc} from './icons.js';
import {languageFor} from './editor.js';
import {DocumentDrag} from './document-drag.js';
import {ExtensionServicesUI} from './extension-services.js';
import {EditorContextMenu} from './editor-context-menu.js';
import {monacoCompletion,completionDetails,completionProviders} from './extension-completions.js';
import {extensionRequests} from './extension-requests.js';
const $=s=>document.querySelector(s);

export function installPreview(host){return new Preview(host);}
class Preview{
  constructor(host){
    this.host=host;host.editor.mount.append(document.getElementById('editor-empty'));this.grouped=false;this.group=null;this.providers=[];
    this.services=new ExtensionServicesUI(host);host.platform.extensionServices=this.services;
    const group=document.createElement('button');group.className='icon-button';group.dataset.action='group-tabs';group.title='Agrupar pestañas por carpeta';group.setAttribute('aria-label',group.title);group.innerHTML=icon('folder');$('.new-tab').after(group);
    this.groups=document.createElement('div');this.groups.className='file-groups';this.groups.setAttribute('aria-label','Grupos de archivos');$('#file-tabs').before(this.groups);
    this.drop=document.createElement('button');this.drop.className='window-drop-target';this.drop.hidden=true;this.drop.innerHTML=icon('plus')+' Soltar en nueva ventana';$('.editor-tabbar').append(this.drop);
    const live=document.createElement('div');live.className='ai-live-control';live.innerHTML='<small>Preguntar no modifica tu archivo.</small><button type="button" id="ai-edit-file" class="secondary-button">Editar archivo…</button>';$('#ai-form').before(live);
    $('#ai-edit-file').onclick=()=>this.safe(()=>host.platform.sendAI($('#ai-input').value,{edit:true}));
    this.context=document.createElement('small');this.context.className='ai-current-document';live.before(this.context);
    const assistantScroll=document.createElement('div');assistantScroll.className='assistant-scroll';$('#assistant-body').prepend(assistantScroll);
    for(const selector of ['#assistant-hero','#ai-actions','.assistant-lantern','#chat-messages']){const item=$(selector);if(item)assistantScroll.append(item);}
    this.documentDrag=new DocumentDrag({...host,panel:$('#editor-panel'),safe:fn=>this.safe(fn),onStart:path=>{this.dragged=path;this.drop.hidden=false;},onEnd:()=>{this.drop.hidden=true;this.dragged=null;},detach:(path,position)=>host.detachEditor(path,position)});
    this.drop.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect='move';};
    this.drop.ondrop=e=>{e.preventDefault();e.stopPropagation();this.safe(async()=>{const data=JSON.parse(e.dataTransfer.getData('application/x-lumen-document'));await this.host.detachEditor(data.path);});this.drop.hidden=true;};
    $('#file-tabs').addEventListener('contextmenu',e=>{const tab=e.target.closest('[data-tab]');if(!tab)return;e.preventDefault();e.stopPropagation();this.fileTabMenu(tab);});
    this.fileTabMenu=tab=>{const path=tab.dataset.tab;
      const paths=[...host.editor.models.keys()],close=async names=>{for(const p of names){await host.closeFile(p);if(host.editor.models.has(p))break;}};
      host.showMenu(tab,[
        {label:'Guardar',icon:'check',shortcut:'Ctrl S',run:()=>host.saveFile(path)},
        {label:'Guardar como…',icon:'file',shortcut:'Ctrl Shift S',run:()=>this.saveAs(path)},
        {label:'Cambiar nombre de archivo…',icon:'rename',run:()=>this.renameFile(path)},
        {label:'Eliminar archivo',icon:'trash',run:()=>this.deleteFile(path)},
        ...(this.canRestoreDeleted?.()?[{label:'Deshacer eliminación',icon:'undo',run:()=>this.restoreDeleted()}]:[]),
        {label:'Mostrar en el explorador',icon:'folder',run:async()=>{await host.openFile(path);host.dock.show('project');host.revealFile(path);}},
        {label:'Copiar ruta relativa',icon:'copy',run:()=>navigator.clipboard.writeText(path)},
        {label:'Copiar ruta',icon:'copy',run:()=>navigator.clipboard.writeText(host.service().workspace.replaceAll('\\','/')+'/'+path)},
        {separator:true},
        {label:'Abrir en otra ventana',icon:'plus',run:()=>this.newWindow(path)},
        {label:this.grouped?'Mostrar pestañas sin grupos':'Agrupar por carpeta',icon:'folder',run:()=>this.toggleGroups()},
        {label:'Ejecutar con Lantern',icon:'play',run:async()=>{await host.openFile(path);await host.studio.lantern.action('start');}},
        {separator:true},
        {label:'Cerrar',icon:'close',run:()=>close([path])},
        {label:'Cerrar los demás',icon:'close',run:()=>close(paths.filter(p=>p!==path))},
        {label:'Cerrar a la derecha',icon:'close',run:()=>close(paths.slice(paths.indexOf(path)+1))},
        {label:'Cerrar guardados',icon:'check',run:()=>close(paths.filter(p=>!host.editor.isDirty(p)))},
        {label:'Cerrar todos',icon:'close',run:()=>close(paths)},
        {separator:true},{label:'Reabrir pestaña cerrada',icon:'undo',shortcut:'Ctrl Shift T',disabled:!this.tabControls?.canReopen(),run:()=>this.tabControls?.reopen()},
      ],path.split('/').at(-1));};
    document.addEventListener('click',e=>{const exec=e.target.closest('[data-extension-execute]');if(exec)this.safe(()=>this.startExtension(exec.dataset.extensionExecute));});
    this.extensionObserver=new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches('.extension-card')||n.querySelector('.extension-card')))))this.extensionButtons();});this.extensionObserver.observe(document.body,{childList:true,subtree:true});
    const viewButton=document.createElement('button');viewButton.className='icon-button';viewButton.title='Vistas de extensiones';viewButton.setAttribute('aria-label',viewButton.title);viewButton.innerHTML=icon('extensions');$('.editor-tabbar').append(viewButton);viewButton.onclick=()=>this.safe(()=>this.extensionViews());
    const load=host.platform.loadContributions.bind(host.platform);host.platform.loadContributions=async(...args)=>{const result=await load(...args);const status=await host.platform.api('/extensions/runtime');this.registerExtensions(status.hosts);return result;};
    host.platform.beforeSave=(path,automatic)=>this.documentSaveEvent(path,'willSave',automatic);
    const afterSave=host.platform.afterSave.bind(host.platform);host.platform.afterSave=async path=>{await this.documentSaveEvent(path,'didSave');await afterSave(path);};
    this.activeChanged();this.renderGroups();this.languageFeatures();
    this.restoreEngines();
  }
  async restoreEngines(){
    if(this.host.platform.disposed)return;
    try{if(this.host.service().trusted&&!this.restoredWorkspace){this.restoredWorkspace=this.host.service().workspace;const [state,metadata]=await Promise.all([this.host.platform.api('/extensions/runtime/restore',{}),this.host.platform.api('/extensions')]);this.extensionMetadata=new Map(metadata.extensions.map(x=>[x.id,x]));this.registerExtensions(state.hosts);for(const [id,error] of Object.entries(state.errors||{}))this.host.notify(id+': '+error,'error');}}
    catch(error){this.host.notify(error.message,'error');}
    if(this.restoredWorkspace===this.host.service().workspace)try{const state=await this.host.platform.api('/extensions/runtime'),signature=JSON.stringify(state.hosts.map(({logs,...host})=>host));if(signature!==this.runtimeSignature)this.registerExtensions(state.hosts);}catch(error){console.warn('Extension capabilities:',error.message);}
    this.restoreTimer=setTimeout(()=>{if(!this.host.service().trusted||this.restoredWorkspace!==this.host.service().workspace)this.restoredWorkspace=null;this.restoreEngines();},2200);
  }
  safe(fn){return Promise.resolve().then(fn).catch(e=>this.host.notify(e.message,'error',7000));}
  activeChanged(){this.context.textContent='Contexto actual · '+(this.host.editor.current||'Abre un archivo para adjuntarlo');this.host.studio.lantern.follow();this.renderGroups();}
  toggleGroups(){this.grouped=!this.grouped;this.renderGroups();}
  renderGroups(){
    const ed=this.host.editor,sets=new Map();for(const path of ed.visiblePaths()){const key=path.includes('/')?path.slice(0,path.lastIndexOf('/')):'Proyecto';if(!sets.has(key))sets.set(key,[]);sets.get(key).push(path);}
    const current=ed.current?.includes('/')?ed.current.slice(0,ed.current.lastIndexOf('/')):'Proyecto';
    this.groups.hidden=!this.grouped||ed.visiblePaths().length<2;
    const signature=JSON.stringify([this.grouped,ed.current,ed.visiblePaths()]);
    if(signature!==this.groupSignature){this.groupSignature=signature;this.groups.innerHTML=[...sets].map(([name,paths])=>`<button class="file-group ${name===current?'active':''}" data-file-group="${esc(name)}" aria-haspopup="menu">${icon('folder')}<span>${esc(name.split('/').at(-1))}</span><small>${paths.length}</small>${icon('chevron-down')}</button>`).join('');this.groups.querySelectorAll('button').forEach(b=>b.onclick=()=>this.host.showMenu(b,sets.get(b.dataset.fileGroup).map(path=>({label:path.split('/').at(-1)+(ed.isDirty(path)?' •':''),icon:'file',run:()=>this.host.openFile(path)})),b.dataset.fileGroup));}
    $('#file-tabs').classList.toggle('is-grouped',this.grouped&&ed.visiblePaths().length>1);
  }
  async newWindow(path='',content){
    if(path&&content===undefined){if(!this.host.editor.models.has(path))await this.host.openFile(path);return this.host.detachEditor(path);}
    if(path&&content===undefined){const r=this.host.editor.models.get(path);content=r?.model?.getValue()??r?.value;}
    if(window.pywebview?.api?.new_window)return window.pywebview.api.new_window(path,content??null);
    const url=new URL(location.href);url.searchParams.set('file',path);const opened=window.open(url,'_blank');if(!opened)throw Error('Permite abrir ventanas en el navegador o utiliza Zénit Desktop.');
  }
  async saveAs(path=this.host.editor.current){
    const ed=this.host.editor;if(!path)return;
    if(ed.current!==path)await this.host.openFile(path);
    if(ed.models.get(ed.current)?.kind==='binary'){this.host.notify('Guarda los bytes desde el editor hexadecimal. Para conservar un parche separado, usa Exportar cambios.');return;}
    if(window.pywebview?.api?.save_as){const result=await window.pywebview.api.save_as(ed.current,ed.getValue());if(!result)return;await this.host.refreshTree();if(result.relative){const fresh=await this.host.api('/file?path='+encodeURIComponent(result.relative));const existing=ed.models.get(result.relative);if(existing){existing.model?.setValue(fresh.content);existing.value=fresh.content;ed.markSaved(fresh);}await this.host.openFile(result.relative);}this.host.notify('Archivo guardado en '+result.path);return;}
    const content=ed.getValue();
    this.host.modal('Guardar como',`<form id="save-as-form"><label>Ruta dentro del proyecto<input id="save-as-path" value="${esc(path)}" required></label><div class="modal-actions"><button class="primary-button">Guardar copia</button></div></form>`);
    $('#save-as-form').onsubmit=e=>{e.preventDefault();this.safe(async()=>{const destination=$('#save-as-path').value.trim();await this.host.api('/save',{path:destination,content,create:true});this.host.closeModal();await this.host.refreshTree();await this.host.openFile(destination);});};
  }
  async downloads(){
    this.host.platform.openPage('downloads',`<section class="downloads-page"><span class="eyebrow">HERRAMIENTAS · PREVIEW</span><h1>Espacio para tus compiladores.</h1><p>Hasta 500 GB por archivo. Transferencia directa a disco, pausa y reanudación cuando el servidor lo permite.</p><form id="download-form"><label>URL HTTPS del distribuidor<input id="download-url" type="url" placeholder="https://…" required></label><label>Nombre del archivo<input id="download-name" placeholder="compilador.zip" required></label><label>SHA-256 del distribuidor · opcional<input id="download-sha" pattern="[a-fA-F0-9]{64}" placeholder="Verificación del archivo"></label><button class="primary-button">${icon('download')}Descargar</button></form><p class="muted-copy">Los paquetes se guardan sin ejecutarlos. Después de instalarlos, configura su ruta en Lenguajes y herramientas.</p><small id="download-location"></small><div id="download-list"></div></section>`);
    $('#download-form').onsubmit=e=>{e.preventDefault();this.safe(async()=>{await this.host.platform.api('/downloads/start',{url:$('#download-url').value,name:$('#download-name').value,sha256:$('#download-sha').value});await this.renderDownloads();});};
    await this.renderDownloads();
  }
  async renderDownloads(){
    clearTimeout(this.downloadTimer);if(!$('#download-list'))return;
    const data=await this.host.platform.api('/downloads');if(!$('#download-list'))return;
    const size=n=>(n/1e9).toLocaleString('es',{maximumFractionDigits:3})+' GB';$('#download-location').textContent=data.directory+' · '+size(data.free)+' libres';
    $('#download-list').innerHTML=data.items.map(x=>`<article class="download-item"><strong>${esc(x.name)}</strong><span>${esc({downloading:'Descargando',paused:'Pausada',verifying:'Verificando',complete:'Completada',error:'Error'}[x.status])}</span><progress max="${x.total||1}" value="${x.total?x.bytes:0}"></progress><small>${size(x.bytes)}${x.total?' / '+size(x.total):''} · ${(x.speed/1e6).toFixed(1)} MB/s</small>${x.error?`<p role="alert">${esc(x.error)}</p>`:''}${x.status==='complete'?`<code>${esc(x.path)}</code>`:`<button class="secondary-button" data-download="${x.id}" data-op="${['downloading','verifying'].includes(x.status)?'pause':'resume'}">${['downloading','verifying'].includes(x.status)?'Pausar':'Reanudar'}</button>`}</article>`).join('')||'<p>No hay descargas.</p>';
    document.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>this.safe(async()=>{await this.host.platform.api('/downloads/'+b.dataset.op,{id:b.dataset.download});await this.renderDownloads();}));this.downloadTimer=setTimeout(()=>this.safe(()=>this.renderDownloads()),1200);
  }
  extensionButtons(){
    document.querySelectorAll('[data-extension-toggle]').forEach(toggle=>{const card=toggle.closest('.extension-card');if(card.querySelector('[data-extension-execute]'))return;const item=this.host.platform.extensionItems?.find(x=>x.id===toggle.dataset.extensionToggle);if(!item?.supported?.includes('runtime'))return;const b=document.createElement('button');b.className='secondary-button small-button';b.dataset.extensionExecute=item.id;b.textContent=this.extensionStartLabel(item.id);toggle.before(b);});
    if($('.tools-content')&&!$('#download-tools-link')){const b=document.createElement('button');b.id='download-tools-link';b.className='secondary-button';b.textContent='Descargar compilador · hasta 500 GB';b.onclick=()=>this.safe(()=>this.downloads());$('.tools-content .section-heading').append(b);}
  }
  async extensionViews(target=null){
    const hosts=(this.runtimeHosts||[]).filter(x=>x.running&&x.views?.length&&(!target||x.id===target.extension));
    this.host.platform.openPage('extension-views',`<section class="extension-views-page"><h3>Vistas de tus extensiones</h3><p>Contenido real de los motores activos. Expande los nodos o ejecuta sus comandos.</p>${hosts.map((h,i)=>`<article class="extension-tree-card" data-extension-tree="${i}"><h4>${esc(h.id)}</h4></article>`).join('')||'<p>Inicia una extensión que registre TreeDataProvider o TreeView para ver su contenido.</p>'}</section>`);
    for(let i=0;i<hosts.length;i++)for(const view of hosts[i].views){if(target&&view.id!==target.view)continue;const section=document.createElement('section');section.className='extension-tree-view';section.innerHTML=`<header><strong>${esc(view.title||view.id)}</strong><button class="icon-button" aria-label="Actualizar ${esc(view.title||view.id)}">${icon('refresh')}</button></header><div class="extension-tree-nodes"></div>`;document.querySelector(`[data-extension-tree="${i}"]`).append(section);const refresh=()=>this.safe(()=>this.treeChildren(hosts[i],view.id,section.lastElementChild));section.querySelector('button').onclick=refresh;await refresh();}
  }
  async treeChildren(ext,view,container,element){
    let data;try{data=await this.host.platform.api('/extensions/runtime/request',{id:ext.id,method:'tree',view,element});}catch(error){if(error.message.includes('Vista de extensión no registrada')){container.textContent='La extensión todavía no ha registrado el proveedor de esta vista.';return;}throw error;}if(!container.isConnected)return;
    container.replaceChildren();
    for(const item of data.items){const row=document.createElement('button');row.className='extension-tree-row';row.title=typeof item.tooltip==='string'?item.tooltip:'';row.innerHTML=icon(item.collapsibleState?'chevron-right':'file')+`<span>${esc(item.label)}</span><small>${esc(item.description||'')}</small>`;container.append(row);const children=document.createElement('div');children.className='extension-tree-children';children.hidden=true;container.append(children);
      if(item.checkboxState!==undefined){const input=document.createElement('input');input.type='checkbox';input.checked=(typeof item.checkboxState==='object'?item.checkboxState.state:item.checkboxState)===1;input.setAttribute('aria-label',item.label);row.before(input);input.onchange=()=>this.safe(()=>this.host.platform.api('/extensions/runtime/request',{id:ext.id,method:'treeCheckbox',view,element:item.key,checkboxState:input.checked?1:0}));}
      row.onclick=()=>this.safe(async()=>{if(item.collapsibleState){children.hidden=!children.hidden;row.setAttribute('aria-expanded',String(!children.hidden));if(!children.hidden)await this.treeChildren(ext,view,children,item.key);}else if(item.command)await this.host.platform.pluginCommand(ext.id+':'+item.command.command,item.command.arguments||[]);});
      if(item.collapsibleState===2){children.hidden=false;row.setAttribute('aria-expanded','true');await this.treeChildren(ext,view,children,item.key);}
    }
  }
  extensionStartLabel(id){
    const p=this.host.platform;if(id!=='nc-lang.nc-language'&&((p.extensionContributions?.iconThemes||[]).some(t=>t.owner===id)||(p.extensionThemes||[]).some(t=>t.owner===id)))return p.t('Aplicar apariencia','Apply appearance');
    return this.runtimeHosts?.some(x=>x.id===id&&x.running)?p.t('Detener motor','Stop engine'):p.t('Iniciar motor','Start engine');
  }
  async startExtension(id){
    const platform=this.host.platform,icons=(platform.extensionContributions.iconThemes||[]).filter(t=>t.owner===id),themes=(platform.extensionThemes||[]).filter(t=>t.owner===id);
    if(id!=='nc-lang.nc-language'&&(icons.length||themes.length)){
      if(icons.length===1)await platform.savePreference('appearance.iconTheme',icons[0].id);
      else if(icons.length)platform.iconThemePicker.open(id);
      else if(themes.length===1)await platform.savePreference('appearance.extensionTheme',themes[0].id);
      else platform.themePicker.open(id);
      return;
    }
    if(this.runtimeHosts?.some(x=>x.id===id&&x.running)){const stopped=await this.host.platform.api('/extensions/runtime/stop',{id});this.registerExtensions(stopped.hosts);return;}
    if(!await this.host.platform.host.ensureTrust())return;
    const graph=await this.host.platform.api('/extensions/dependencies?id='+encodeURIComponent(id));
    const dependencies=graph.extensions.filter(x=>x.id!==id).map(x=>x.id+(x.executable?' (motor)':' (recursos)'));
    if(!await this.host.platform.confirmRoutine('Ejecutar '+id,'Este plugin ejecutará su motor con tus permisos de usuario. Tendrá acceso al equipo y a los documentos que consultes. El proceso separado evita que bloquee la interfaz; no es un aislamiento de seguridad.'+(dependencies.length?'\n\nDependencias que se activarán en el mismo proceso:\n'+dependencies.join('\n'):''),'Autorizar motor'))return;
    const data=await this.host.platform.api('/extensions/runtime/start',{id,consent:true});this.registerExtensions(data.hosts);const engine=data.hosts.find(x=>x.id===id);this.host.notify(engine?.unsupportedApis?.length?'Motor con servicios pendientes: '+engine.unsupportedApis.join(', '):engine?.engine||'Motor iniciado. Comandos disponibles en la paleta.',engine?.unsupportedApis?.length?'error':'info');
  }
  registerExtensions(hosts,{force=false}={}){
    this.runtimeSignature=JSON.stringify(hosts.map(({logs,...host})=>host));
    const providerSignature=JSON.stringify([this.host.service().workspace,hosts.map(({id,running,providers,tokens,fileDecorations})=>({id,running,providers,tokens,fileDecorations}))]);
    const keepProviders=!force&&providerSignature===this.providerSignature;this.providerSignature=providerSignature;
    if(!keepProviders){for(const p of this.providers)p.dispose?.();this.providers=[];}
    this.runtimeHosts=hosts;this.services.terminalLinkHosts=hosts.filter(x=>x.running&&x.terminalLinks);document.querySelectorAll('[data-extension-execute]').forEach(b=>b.textContent=this.extensionStartLabel(b.dataset.extensionExecute));const platform=this.host.platform,m=window.monaco,ed=this.host.editor;
    if(!keepProviders)this.providers.push(explorerDecorations(this.host,hosts.filter(x=>x.running&&x.fileDecorations)));
    const doc=model=>{const path=[...ed.models].find(([,r])=>r.model===model)?.[0]||ed.current;return {path,text:model?.getValue()??ed.getValue(),language:languageFor(path)};};
    const relativeUri=value=>{const raw=typeof value==='string'?value:(value?.fsPath||value?.external||value?.path||'');const absolute=decodeURIComponent(raw.replace(/^file:\/\//,'')).replaceAll('\\','/').replace(/^\/(?:([A-Za-z]:))/, '$1');const root=this.host.service().workspace.replaceAll('\\','/').replace(/\/$/,'');if(absolute.toLowerCase().startsWith(root.toLowerCase()+'/'))return absolute.slice(root.length+1);if(/^(?:[A-Za-z]:|\/)/.test(absolute))throw Error('La definición está fuera del proyecto abierto.');return absolute;};
    const requests=keepProviders?null:extensionRequests(platform.api.bind(platform));if(requests)this.providers.push(requests);
    const callResult=(ext,kind,model,extra={},token)=>{const version=model?.getVersionId();return requests.request({id:ext.id,method:'provide',kind,document:doc(model),...extra},model,token).then(x=>model&&(model.isDisposed()||model.getVersionId()!==version)?{items:[],incomplete:false,cancelled:true}:x);};
    const call=(ext,kind,model,extra={},token)=>callResult(ext,kind,model,extra,token).then(x=>x.items);
    const mr=r=>r?new m.Range(r.start.line+1,r.start.character+1,r.end.line+1,r.end.character+1):undefined;
    if(!this.extensionCommandBridge)this.extensionCommandBridge=m?.editor.registerCommand('lumen.extension.command',(_,id,args)=>this.safe(()=>platform.pluginCommand(id,args)));
    if(!this.extensionEditBridge)this.extensionEditBridge=m?.editor.registerCommand('zenit.extension.workspaceEdit',async(_,edit,path,version,command,args)=>{
      try{
        const record=ed.models.get(path);if(!record?.model||record.model.getVersionId()!==version)throw Error('El archivo cambió. Solicita de nuevo la acción.');
        const root=this.host.service().workspace.replaceAll('\\','/').replace(/\/$/,''),documents=[...ed.models.values()].map(r=>({uri:/^(?:[A-Za-z]:[\\/]|\/)/.test(r.path)?r.path:root+'/'+r.path,text:r.model?.getValue()??r.value}));
        const result=await platform.api('/extensions/applyEdit',{edit,documents});await this.services.event({command:'zenit.workspace.edit',edit:result});
        if(command)await platform.pluginCommand(command,args);return result.applied;
      }catch(error){this.host.notify(error.message,'error');throw error;}
    });
    this.runtimeCommands=new Map();
    for(const ext of hosts.filter(x=>x.running)){
      for(const command of ext.commands)this.runtimeCommands.set(ext.id+':'+command.id,{ext:ext.id,...command});
      if(ext.tasks?.length)this.runtimeCommands.set(ext.id+':__zenit.tasks',{ext:ext.id,id:'__zenit.tasks',title:'Tareas · '+(this.extensionMetadata?.get(ext.id)?.displayName||ext.id),tasks:true});
      if(ext.notebooks)this.runtimeCommands.set(ext.id+':__zenit.notebook',{ext:ext.id,id:'__zenit.notebook',title:'Abrir cuaderno · '+ext.id,notebook:true});
      if(keepProviders||!m)continue;
      for(const token of ext.tokens||[])this.providers.push(m.languages.setMonarchTokensProvider(token.language,{tokenizer:{root:token.rules.map(r=>[new RegExp(r.pattern,r.flags||''),r.token])}}));
      const contents=value=>(Array.isArray(value)?value:[value]).filter(Boolean).map(c=>typeof c==='string'?{value:c}:{value:c.value||String(c),isTrusted:false});
      for(const p of completionProviders(ext.providers)){const language=p.language;const editing=editingProvider(ext,p,{m,ed,call,mr,relativeUri,requests,host:this.host});if(editing)this.providers.push(editing);
        if(p.kind==='hover')this.providers.push(m.languages.registerHoverProvider(language,{provideHover:async(model,pos,token)=>{const items=await call(ext,'hover',model,{position:{line:pos.lineNumber-1,character:pos.column-1}},token);return items.length?{contents:items.flatMap(i=>contents(i.contents)),range:mr(items[0].range)}:null;}}));
        if(p.kind==='signature')this.providers.push(m.languages.registerSignatureHelpProvider(language,{signatureHelpTriggerCharacters:p.triggers||[],provideSignatureHelp:async(model,pos,token)=>{const items=await call(ext,'signature',model,{position:{line:pos.lineNumber-1,character:pos.column-1}},token);return items.length?{value:items[0],dispose(){}}:null;}}));
        if(p.kind==='links')this.providers.push(m.languages.registerLinkProvider(language,{provideLinks:async(model,token)=>({links:(await call(ext,'links',model,{},token)).flatMap(i=>{const raw=typeof i.target==='string'?i.target:i.target?.external;try{const url=new URL(raw);return ['http:','https:','mailto:'].includes(url.protocol)?[{range:mr(i.range),url:url.href}]:[];}catch{return [];}}),dispose(){}})}));
        if(p.kind==='folding')this.providers.push(m.languages.registerFoldingRangeProvider(language,{provideFoldingRanges:async(model,context,token)=>(await call(ext,'folding',model,{},token)).map(r=>({start:r.start+1,end:r.end+1,kind:r.kind==='comment'?m.languages.FoldingRangeKind.Comment:r.kind==='imports'?m.languages.FoldingRangeKind.Imports:r.kind==='region'?m.languages.FoldingRangeKind.Region:undefined}))}));
        if(p.kind==='rename')this.providers.push(m.languages.registerRenameProvider(language,{provideRenameEdits:async(model,pos,newName,token)=>{
          const version=model.getVersionId(),guards=[...ed.models.values()].filter(r=>r.model).map(r=>[r.model,r.model.getVersionId()]);
          const ncBuffers=()=>[...ed.models].filter(([path,r])=>r.model&&/\.(?:n|nc)$/i.test(path)).map(([path,r])=>({path,text:r.model.getValue()}));
          const data=await callResult(ext,'rename',model,{newName,position:{line:pos.lineNumber-1,character:pos.column-1},...(ext.id==='nc-lang.nc-language'?{buffers:ncBuffers()}:{})},token);
          if(data.cancelled)return {edits:[]};
          if(guards.some(([m,v])=>m.isDisposed()||m.getVersionId()!==v))throw Error('Un archivo abierto cambió durante el renombrado. Solicítalo de nuevo.');
          const options=data.refactor?{verify:()=>platform.api('/nc/refactor/verify',{id:data.refactor.id,buffers:ncBuffers()})}:{};
          return platform.reviewedEdits.reviewWorkspace({changes:data.items.flatMap(i=>i.changes||[])},model,version,data.refactor?'Renombrar entre módulos · NCC comprobado':'Renombrar símbolo · revisar cambios',options);
        }}));
        if(p.kind==='format')this.providers.push(m.languages.registerDocumentFormattingEditProvider(language,{provideDocumentFormattingEdits:async(model,options,token)=>(await call(ext,'format',model,{options},token)).map(e=>({range:mr(e.range),text:e.newText}))}));
        if(p.kind==='semantic'&&p.legend)this.providers.push(m.languages.registerDocumentSemanticTokensProvider(language,{getLegend:()=>ed.semanticStyles?.legend||p.legend,provideDocumentSemanticTokens:async(model,lastResultId,token)=>{const items=await call(ext,'semantic',model,{},token);return items.length?{data:ed.semanticStyles?ed.semanticStyles.rewrite(items[0].data,p.legend,model.getLanguageId()):new Uint32Array(items[0].data),resultId:items[0].resultId}:null;},releaseDocumentSemanticTokens(){}}));
        if(p.kind==='symbols')this.providers.push(m.languages.registerDocumentSymbolProvider(language,{provideDocumentSymbols:async(model,token)=>{const convert=s=>({...s,range:mr(s.range),selectionRange:mr(s.selectionRange||s.range),children:(s.children||[]).map(convert)});return (await call(ext,'symbols',model,{},token)).map(convert);}}));
        if(p.kind==='codelens')this.providers.push(m.languages.registerCodeLensProvider(language,{provideCodeLenses:async(model,token)=>({lenses:(await call(ext,'codelens',model,{},token)).map(c=>({...c,range:mr(c.range),command:c.command?{id:'lumen.extension.command',title:c.command.title,arguments:[ext.id+':'+c.command.command,c.command.arguments||[]]}:undefined})),dispose(){}})}));
        if(p.kind==='diagnostics'){
          let timer,poll,disposed=false;const refresh=()=>{clearTimeout(timer);clearTimeout(poll);timer=setTimeout(async()=>{const model=ed.view.getModel();if(disposed||!model||doc(model).language!==language)return;const version=model.getVersionId(),path=doc(model).path;try{const items=await call(ext,'diagnostics',model);if(!model.isDisposed()&&model.getVersionId()===version){const markers=items.map(d=>{const line=d.startLineNumber||d.line||1,column=d.startColumn||d.column||1;const range=model.validateRange(new m.Range(line,column,d.endLineNumber||d.endLine||line,d.endColumn||column+1));return {...range,message:String(d.message||''),severity:typeof d.severity==='number'?d.severity:({warning:m.MarkerSeverity.Warning,info:m.MarkerSeverity.Info,hint:m.MarkerSeverity.Hint}[d.severity]||m.MarkerSeverity.Error),source:ext.id};});ed.setDiagnostics(path,markers,'plugin-'+ext.id);if(!disposed&&ed.view.getModel()===model)poll=setTimeout(refresh,1800);}}catch(e){this.host.notify(e.message,'error');}},450);};
          const a=ed.view.onDidChangeModelContent(refresh),b=ed.view.onDidChangeModel(refresh);window.addEventListener('lumen:editor-active',refresh);window.addEventListener('lumen:document-changed',refresh);this.providers.push({dispose(){disposed=true;clearTimeout(timer);clearTimeout(poll);a.dispose();b.dispose();window.removeEventListener('lumen:editor-active',refresh);window.removeEventListener('lumen:document-changed',refresh);for(const [path] of ed.models)ed.setDiagnostics(path,[],'plugin-'+ext.id);}});refresh();
        }
        if(p.kind==='inlineCompletion')this.providers.push(m.languages.registerInlineCompletionsProvider(language,{
          provideInlineCompletions:async(model,pos,context,token)=>{
            if(token.isCancellationRequested)return {items:[]};
            const version=model.getVersionId(),items=await call(ext,'inlineCompletion',model,{position:{line:pos.lineNumber-1,character:pos.column-1},context:{triggerKind:context.triggerKind===1?0:1}},token);
            if(token.isCancellationRequested||model.isDisposed()||model.getVersionId()!==version)return {items:[]};
            return {items:items.map(i=>({insertText:typeof i.insertText==='object'?{snippet:i.insertText.value}:i.insertText,range:mr(i.range),filterText:i.filterText,command:i.command?{id:'lumen.extension.command',title:i.command.title||'',arguments:[ext.id+':'+i.command.command,i.command.arguments||[]]}:undefined}))};
          },freeInlineCompletions(){}
        }));
        if(p.kind==='completion'){
          const origins=new WeakMap();
          this.providers.push(m.languages.registerCompletionItemProvider(language,{triggerCharacters:p.triggers||[],
            provideCompletionItems:async(model,pos,context,token)=>{
              if(token?.isCancellationRequested)return {suggestions:[]};const version=model.getVersionId(),word=model.getWordUntilPosition(pos),options={monaco:m,mapRange:mr,range:new m.Range(pos.lineNumber,word.startColumn,pos.lineNumber,word.endColumn)};
              const data=await callResult(ext,'completion',model,{position:{line:pos.lineNumber-1,character:pos.column-1},context:{triggerKind:context?.triggerKind??0,triggerCharacter:context?.triggerCharacter}},token);
              if(token?.isCancellationRequested)return {suggestions:[]};
              return {incomplete:!!data.incomplete,suggestions:data.items.map(raw=>{const item=monacoCompletion(raw,options);if(raw._lumenCompletion)origins.set(item,{model,version,key:raw._lumenCompletion,options});return item;})};
            },
            resolveCompletionItem:async(item,token)=>{
              const origin=origins.get(item);if(!origin||token?.isCancellationRequested||origin.model.isDisposed()||origin.model.getVersionId()!==origin.version)return item;
              try{const data=await requests.request({id:ext.id,method:'resolveCompletion',completion:origin.key,document:doc(origin.model)},origin.model,token);if(data.cancelled||token?.isCancellationRequested||origin.model.isDisposed()||origin.model.getVersionId()!==origin.version)return item;return completionDetails(item,data.item,origin.options);}
              catch(error){if(!origin.model.isDisposed()&&origin.model.getVersionId()===origin.version)console.warn('No se pudo ampliar la sugerencia de '+ext.id+': '+error.message);return item;}
            }
          }));
        }
        if(p.kind==='inlay')this.providers.push(m.languages.registerInlayHintsProvider(language,{provideInlayHints:async(model,range,token)=>({hints:(await call(ext,'inlay',model,{range:{start:{line:range.startLineNumber-1,character:range.startColumn-1},end:{line:range.endLineNumber-1,character:range.endColumn-1}}},token)).map(h=>({...h,position:{lineNumber:h.position.line+1,column:h.position.character+1}})),dispose(){}})}));
        if(p.kind==='references')this.providers.push(m.languages.registerReferenceProvider(language,{provideReferences:async(model,pos,context,token)=>(await call(ext,'references',model,{position:{line:pos.lineNumber-1,character:pos.column-1}},token)).map(d=>{const path=relativeUri(d.uri);return {uri:ed.models.get(path)?.model?.uri||m.Uri.parse('file:///'+path),range:mr(d.range)};})}));
        if(p.kind==='definition')this.providers.push(m.languages.registerDefinitionProvider(language,{provideDefinition:async(model,pos,token)=>{const items=await call(ext,'definition',model,{position:{line:pos.lineNumber-1,character:pos.column-1}},token);return items.map(d=>{const path=d.path||(d.uri||d.targetUri?relativeUri(d.uri||d.targetUri):doc(model).path);return {uri:ed.models.get(path)?.model?.uri||m.Uri.parse('file:///'+path),range:mr(d.range||d.targetSelectionRange||d.targetRange)};});}}));
      }
    }
    if(!this.oldPluginCommand)this.oldPluginCommand=platform.pluginCommand.bind(platform);
    platform.pluginCommand=async(id,args=[])=>{
      const command=this.runtimeCommands.get(id);if(!command)return this.oldPluginCommand(id);
      const snapshot={path:ed.current,text:ed.getValue()},model=ed.models.get(ed.current)?.model;
      if(command.notebook){if(!/\.ipynb$/i.test(ed.current||''))throw Error('Abre primero un archivo .ipynb del proyecto.');if(ed.isDirty(ed.current))await this.host.saveFile(ed.current);const uri=m.Uri.file(this.host.service().workspace+'/'+ed.current).toString();return platform.api('/extensions/runtime/request',{id:command.ext,method:'notebook',action:'open',uri});}
      const data=await platform.api('/extensions/runtime/request',{id:command.ext,method:command.tasks?'tasks':'command',command:command.id,arguments:args,document:doc()});
      const edits=[];
      for(const e of data.effects||[]){
        if(e.treeView)await this.extensionViews({extension:command.ext,view:e.treeView});
        if(e.message)this.host.notify(e.message);
        if(e.clipboard!==undefined)await navigator.clipboard.writeText(String(e.clipboard));
        if(e.open)await this.host.openFile(relativeUri(e.open));
        if(e.virtualDocument){const d=e.virtualDocument;document.dispatchEvent(new CustomEvent('zenit:code-detail',{detail:{kind:'documentation',title:d.title,context:{path:d.uri},text:d.text}}));}
        if(e.url){const u=new URL(e.url);if(!['https:','http:'].includes(u.protocol))throw Error('El enlace de la extensión debe usar HTTPS o HTTP.');window.open(u.href,'_blank','noopener,noreferrer');}
        if(e.output!==undefined)this.host.modal(e.title||'Salida de extensión',`<pre class="extension-output">${esc(e.output)}</pre>`);
        if(e.terminal!==undefined){
          const profiles=await platform.api('/terminals/profiles');const profile=profiles.profiles.find(p=>p.id===platform.prefs['terminal.defaultProfile'])||profiles.profiles[0];
          if(!profile)throw Error('No hay un perfil de terminal disponible para la extensión.');
          const terminal=await platform.openTerminal(profile.id);if(terminal)await platform.terminals.get(terminal.id).input.write(String(e.terminal)+'\r');
        }
        if(e.edits){if(relativeUri(e.path)!==snapshot.path)throw Error('Esta propuesta modifica varios archivos. La revisión del plugin admite el archivo activo en esta preview.');edits.push(...e.edits);}
      }
      if(edits.length){
        if(!model||model.isDisposed()||model.getValue()!==snapshot.text)throw Error('El archivo cambió durante la propuesta de la extensión.');
        const changes=edits.map(e=>{const range=mr(e.range);const valid=model.validateRange(range);if(!m.Range.equalsRange(range,valid))throw Error('La extensión devolvió un rango de edición inválido.');return {start:model.getOffsetAt(range.getStartPosition()),end:model.getOffsetAt(range.getEndPosition()),text:e.newText};}).sort((a,b)=>b.start-a.start);
        let text=snapshot.text,last=text.length;for(const change of changes){if(change.end>last)throw Error('La extensión devolvió ediciones solapadas.');text=text.slice(0,change.start)+change.text+text.slice(change.end);last=change.start;}
        return platform.reviewCode(text,snapshot);
      }
      if(typeof data.result?.text==='string')return platform.reviewCode(data.result.text,snapshot);if(typeof data.result==='string')this.host.notify(data.result);
    };
    platform.host.setPluginCommands([...platform.extensionContributions.commands,...[...this.runtimeCommands].map(([id,c])=>({id,title:c.title}))]);
  }
  async documentSaveEvent(path,method,automatic=false){
    const ed=this.host.editor,record=ed.models.get(path),model=record?.model;if(!record)return;
    for(const ext of (this.runtimeHosts||[]).filter(x=>x.running)){
      const text=model?.getValue()??record.value,version=model?.getVersionId();
      let result;try{result=await this.host.platform.api('/extensions/runtime/request',{id:ext.id,method,reason:automatic?2:1,document:{path,text,version,language:languageFor(path),dirty:ed.isDirty(path)}});}catch(error){this.host.notify(ext.id+': '+error.message,'error');continue;}
      if(method!=='willSave'||!result.edits?.length)continue;
      if(!model||model.isDisposed()||model.getVersionId()!==version)throw Error('El archivo cambió antes de guardar. Repite el guardado.');
      const edits=result.edits.map(e=>{const r=e.range;const range=new monaco.Range(r.start.line+1,r.start.character+1,r.end.line+1,r.end.character+1);if(typeof e.newText!=='string'||!monaco.Range.equalsRange(range,model.validateRange(range)))throw Error('La extensión devolvió una edición de guardado inválida.');return {range,text:e.newText};});
      const ordered=edits.map(e=>[model.getOffsetAt(e.range.getStartPosition()),model.getOffsetAt(e.range.getEndPosition())]).sort((a,b)=>a[0]-b[0]);
      if(ordered.some((r,i)=>i&&r[0]<ordered[i-1][1]))throw Error('La extensión devolvió ediciones de guardado solapadas.');
      model.pushStackElement();model.pushEditOperations(null,edits,()=>null);model.pushStackElement();record.value=model.getValue();
    }
  }
  languageFeatures(){
    const m=window.monaco;if(!m)return;
    this.contextMenu=new EditorContextMenu(this);
    this.editorOpener=m.editor.registerEditorOpener({openCodeEditor:async(source,resource,selection)=>{if(resource.scheme!=='file')return false;this.host.platform.editorDepth?.beforeJump();const ed=this.host.editor,path=[...ed.models].find(([,r])=>r.model?.uri.toString()===resource.toString())?.[0]||resource.path.replace(/^\/+/, '');await this.host.openFile(path);if(selection?.startLineNumber){ed.view.setSelection(selection);ed.view.revealRangeInCenter(selection);}else if(selection?.lineNumber){ed.view.setPosition(selection);ed.view.revealPositionInCenter(selection);}ed.view.focus();this.host.platform.editorDepth?.afterJump();return true;}});
    for(const defaults of [m.languages.typescript?.typescriptDefaults,m.languages.typescript?.javascriptDefaults])defaults?.setInlayHintsOptions?.({includeInlayParameterNameHints:'all',includeInlayVariableTypeHints:true,includeInlayFunctionLikeReturnTypeHints:true,includeInlayPropertyDeclarationTypeHints:true});
    const actions=view=>{
    this.contextMenu.attach(view);
    view.updateOptions({inlayHints:{enabled:'on'},'semanticHighlighting.enabled':this.host.editor.extensionTheme?.data?.semanticHighlighting!==false});
    view.addAction({id:'lumen.goToDefinition',label:'Ir a definición · F12',keybindings:[m.KeyCode.F12],run:ed=>ed.trigger('lumen','editor.action.revealDefinition',{})});
    for(const [id,label,run] of [
      ['lantern','Lantern: ejecutar este búfer',()=>this.host.studio.lantern.action('start')],
      ['save','Guardar archivo',()=>this.host.saveFile(this.host.editor.current)],
      ['saveAs','Guardar como…',()=>this.saveAs()],
      ['newWindow','Abrir en otra ventana',()=>this.newWindow(this.host.editor.current)],
      ['explain','Preguntar a la IA sobre este código',()=>{this.host.dock.show('assistant');$('#ai-input').value='Explica este código y qué mejorarías.';$('#ai-input').focus();}],
    ])view.addAction({id:'lumen.context.'+id,label,contextMenuGroupId:'9_lumen',run:()=>this.safe(run)});
    };actions(this.host.editor.view);this.host.editor.callbacks.pane=actions;
    const requested=new URLSearchParams(location.search).get('file');if(requested)this.safe(()=>this.host.openFile(requested));
  }
}
