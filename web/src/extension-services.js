import {ExtensionOutputUI} from './extension-output.js';
import {escapeHTML as esc,icon} from './icons.js';
import {ExtensionQuickInputUI} from './extension-quickinput.js';
import {EditorDecorations} from './editor-decorations.js';
import {sameBufferText} from './buffer-text.js';

export class ExtensionServicesUI {
  constructor(host){this.owner=crypto.randomUUID();this.host=host;this.outputUI=new ExtensionOutputUI(host);this.quickinput=new ExtensionQuickInputUI(host);this.panels=new Map();this.disposed=false;this.message=e=>this.receive(e);window.addEventListener('message',this.message);this.resize=new ResizeObserver(()=>this.layout());this.resize.observe(document.getElementById('editor-panel'));this.poll();}
  layout(){const panel=document.getElementById('editor-panel').getBoundingClientRect(),mount=document.getElementById('editor-mount').getBoundingClientRect();for(const state of this.panels.values())if(state.node)state.node.style.top=Math.max(54,mount.top-panel.top)+'px';}
  async event(event){
    const h=this.host,p=h.platform,ed=h.editor;
    if(event.command==='zenit.editor.options'){
      const model=ed.models.get(event.path)?.model,o=event.options;if(!model)return;
      const opts={};if(Number.isInteger(o.tabSize))opts.tabSize=o.tabSize;if(typeof o.insertSpaces==='boolean')opts.insertSpaces=o.insertSpaces;if(Number.isInteger(o.indentSize)||o.indentSize==='tabSize')opts.indentSize=o.indentSize;
      model.updateOptions(opts);if(o.tabSize==='auto'||o.insertSpaces==='auto')model.detectIndentation(model.getOptions().insertSpaces,model.getOptions().tabSize);
      if(ed.current===event.path){const view=ed.activeView?.()||ed.view;view?.updateOptions({...o.cursorStyle?{cursorStyle:['line','block','underline','line-thin','block-outline','underline-thin'][o.cursorStyle-1]}:{},...o.lineNumbers!==undefined?{lineNumbers:['off','on','relative','interval'][o.lineNumbers]}:{}});}return;
    }
    if(event.command==='zenit.editor.close'){
      if(event.owner!==this.owner)return;
      for(const path of event.paths)if(ed.models.has(path))await h.closeFile(path);
      await p.api('/extensions/pick',{id:event.id,value:event.paths.every(path=>!ed.models.has(path))});return;
    }
    if(event.command==='zenit.editor.reveal'){
      if(ed.current!==event.path)return;const r=event.range,range={startLineNumber:r.start.line+1,startColumn:r.start.character+1,endLineNumber:r.end.line+1,endColumn:r.end.character+1},view=ed.activeView?.()||ed.view;
      if(event.revealType===1)view?.revealRangeInCenter(range);else if(event.revealType===2)view?.revealRangeInCenterIfOutsideViewport(range);else if(event.revealType===3)view?.revealRangeAtTop(range);else view?.revealRange(range);return;
    }
    if(event.command==='zenit.dependencies.changed'){
      if(event.workspace!==h.service().workspace)return;
      const profiles=new Set(event.profiles||[]);p.languageRefresh=true;
      try{
        for(const session of [...p.lspSessions.values()])if(session.languages.some(x=>event.languages.includes(x))){profiles.add(session.profile);await p.stopLSP(session.id);}
        await p.loadContributions();
        for(const profile of profiles)if(![...p.lspSessions.values()].some(s=>s.profile===profile))await p.startLSP(profile,true);
      }finally{p.languageRefresh=false;}
      if(!event.profiles)h.notify(p.t('Dependencias integradas. Las herramientas activas se han actualizado.','Dependencies integrated. Active language tools refreshed.'));return;
    }
    if(event.command==='zenit.trust.changed'){p.host.setTrusted(event.trusted);p.host.setTrustSource?.(event.source);if(!event.trusted)p.workspaceChanged();return;}
    if(event.command==='zenit.preferences.changed'){await p.syncPreferences();return;}
    if(event.command==='zenit.studio.changed'){await p.host.studio?.syncProfile();return;}
    if(event.command==='zenit.tree.changed'){await p.host.refreshTree();return;}
    if(event.command==='zenit.contributions.changed'){await p.loadContributions();return;}
    if(event.command==='zenit.files.changed'){await p.melodyFiles.reload(event.paths||[]);return;}
    if(event.command==='zenit.output'){this.outputUI.event(event);return;}
    if(event.command==='zenit.pick')return this.pick(event);
    if(event.command==='zenit.quickinput')return this.quickinput.update(event);
    if(event.command==='zenit.document.saved'){
      const buffer=event.buffer,record=ed.models.get(buffer.path);if(record&&(record.model?.getValue()??record.value)===buffer.text){record.savedValue=buffer.text;record.revision=buffer.revision;ed.callbacks.change?.(buffer.path,false);h.renderTabs();}return;
    }
    if(event.command==='zenit.terminal.show'){
      if(!p.terminals.has(event.terminal)){const data=await p.api('/terminals');const t=data.sessions.find(x=>x.id===event.terminal);if(t)await p.attachTerminal(t);}else p.selectTerminal(event.terminal);
      return;
    }
    if(event.command==='zenit.terminal.hide'){if(p.activeTerminal===event.terminal)p.useConsole();return;}
    if(event.command==='zenit.debug.show'){await h.studio.debug();return;}
    if(event.command==='zenit.command'){
      if(event.request){
        // All auxiliary windows share the event stream. Only the main workbench
        // owns these global controls and may acknowledge the same request.
        if(new URLSearchParams(location.search).has('panel'))return;
        let result={ok:true};try{
          if(event.id==='workbench.action.selectIconTheme'){p.iconThemePicker.open();if(!document.querySelector('.icon-theme-picker')?.getClientRects().length)throw Error('No se pudo abrir el selector de iconos.');}
          else if(event.id==='workbench.action.selectTheme'){p.themePicker.open();if(!document.querySelector('.theme-picker')?.getClientRects().length)throw Error('No hay temas instalados para abrir el selector.');}
          else if(event.id==='workbench.action.showCommands')h.studio.host.palette('>');
          else if(event.id==='workbench.action.quickOpen')h.studio.host.palette(typeof event.arguments?.[0]==='string'?event.arguments[0]:'');
          else if(event.id==='workbench.action.openSettings')await p.settings();
          else throw Error('Comando visual no implementado.');
        }catch(error){result={ok:false,error:error.message};}
        await p.api('/extensions/pick',{id:event.request,value:result});return;
      }
      if(event.id==='workbench.action.reloadWindow')location.reload();
      if(event.id==='workbench.action.terminal.focus')h.dock.show('console');
      return;
    }
    if(event.command!=='zenit.workspace.edit')return;
    const change=event.edit;
    for(const resource of change.resources||[]){
      if(resource.kind==='rename')for(const path of [...ed.models.keys()])if(path===resource.oldPath||path.startsWith(resource.oldPath+'/')){
        const old=ed.models.get(path),active=ed.current===path,text=old.model?.getValue()??old.value,next=resource.path+path.slice(resource.oldPath.length);ed.close(path);ed.open({...old,path:next,content:text},{activate:active});ed.models.get(next).savedValue=old.savedValue;
      }
      if(resource.kind==='delete')for(const path of [...ed.models.keys()])if(path===resource.path||path.startsWith(resource.path+'/'))ed.close(path);
    }
    for(const buffer of change.buffers||[]){
      const desktop=h.studio.desktop,known=desktop?.shared.get(buffer.path);
      // Polling may already have applied this revision, followed by a local
      // undo. A late copy of its event must not put the extension text back.
      if(known&&known.sequence>=buffer.sequence)continue;
      let record=ed.models.get(buffer.path);
      if(record?.kind==='binary')continue;
      if(!record){ed.open({path:buffer.path,content:buffer.before},{activate:false});record=ed.models.get(buffer.path);}
      const text=record.model?.getValue()??record.value;
      if(!sameBufferText(text,buffer.text)){
        if(!sameBufferText(text,buffer.before)){h.notify('Hay cambios simultáneos en '+buffer.path+'. El búfer local se conserva.','error');continue;}
        const applying=desktop?.applying;if(desktop)desktop.applying=true;
        try{
          if(record.model){record.model.pushStackElement();record.model.pushEditOperations([],[{range:record.model.getFullModelRange(),text:buffer.text}],()=>null);record.model.pushStackElement();}
          else{record.value=buffer.text;if(ed.current===buffer.path)ed.setValue(buffer.text);}
        }finally{if(desktop)desktop.applying=applying;}
      }
      // Track the accepted server revision before the next user edit. Undo is
      // then published as a new local change instead of overwritten by a poll.
      desktop?.acknowledgeBuffer(buffer);
    }
    h.renderTabs();await h.refreshTree();
  }
  async pick(event){
    const h=this.host,opts=event.options||{},items=event.items||[];
    const value=await new Promise(resolve=>{
      let done=false;const finish=value=>{if(done)return;done=true;observer.disconnect();h.closeModal();resolve(value);};
      h.modal(opts.title||'Seleccionar',`<input id="extension-pick-search" class="extension-pick-search" placeholder="${esc(opts.placeHolder||'Buscar…')}" aria-label="Buscar opciones"><div class="extension-pick-list"></div>${opts.canPickMany?'<div class="modal-actions"><button class="primary-button" id="extension-pick-accept">Aceptar</button></div>':''}`);
      const container=document.querySelector('.extension-pick-list'),selected=new Set(items.flatMap((x,i)=>x.picked?[i]:[]));
      const render=query=>{container.replaceChildren();items.forEach((item,index)=>{if(item.kind===-1||!`${item.label} ${item.description||''} ${item.detail||''}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()))return;const button=document.createElement('button');button.className='extension-pick-option';button.innerHTML=`${opts.canPickMany?`<input type="checkbox" tabindex="-1" ${selected.has(index)?'checked':''}>`:''}<span><strong>${esc(item.label)}</strong><small>${esc(item.description||'')}</small><small>${esc(item.detail||'')}</small></span>`;button.onclick=()=>{if(opts.canPickMany){selected.has(index)?selected.delete(index):selected.add(index);render(query);}else finish(index);};container.append(button);});};
      const observer=new MutationObserver(()=>{if(document.querySelector('#modal-backdrop').classList.contains('hidden'))finish(null);});observer.observe(document.querySelector('#modal-backdrop'),{attributes:true,attributeFilter:['class']});
      const search=document.getElementById('extension-pick-search');search.oninput=()=>render(search.value);search.onkeydown=e=>{if(e.key==='Enter'&&!opts.canPickMany){e.preventDefault();container.querySelector('button')?.click();}};document.getElementById('extension-pick-accept')?.addEventListener('click',()=>finish([...selected]));render('');
    });
    await h.platform.api('/extensions/pick',{id:event.id,value});
  }
  async poll(){
    if(this.disposed)return;
    try{
      const {panels,quickinputs=[],statusItems=[],outputs=[],editorDecorations=[]}=await this.host.platform.api('/extensions/services');
      this.editorDecorations ||= new EditorDecorations(this.host);this.editorDecorations.sync(editorDecorations);
      this.syncTerminalLinks();
      this.status(statusItems);this.outputUI.sync(outputs);
      await this.syncEditors();
      if(!this.quickinput.root)for(const input of quickinputs)if(input.visible)this.quickinput.update(input);
      const ids=new Set(panels.filter(x=>x.visible).map(x=>x.id));
      for(const [id,state] of this.panels)if(!ids.has(id)){this.remove(state);this.panels.delete(id);}
      for(const panel of panels){if(!panel.visible)continue;let state=this.panels.get(panel.id);
        if(!state){state={panel,seq:0,urls:[]};this.panels.set(panel.id,state);await this.render(state);this.show(state);}else if(state.panel.html!==panel.html){state.panel=panel;await this.render(state);}else {const previous=state.panel;state.panel=panel;this.title(state);if(previous.revision!==panel.revision&&panel.revealSequence!==previous.revealSequence)this.show(state);}
        for(const item of panel.messages)if(item.seq>state.seq&&state.loaded){state.frame.contentWindow.postMessage(item.message,'*');state.seq=item.seq;}
      }
    }catch(error){if(!this.disposed)console.warn('Extension services:',error.message);}
    this.timer=setTimeout(()=>this.poll(),500);
  }
  renderOutput(){this.outputUI.setVisible(true);return this.outputUI.render();}
  status(items){
    const ed=this.host.editor,language=ed.view?.getModel()?.getLanguageId(),path=ed.current;
    const matches=selector=>!selector||[selector].flat().some(s=>typeof s==='string'?s==='*'||s===language:(!s.language||s.language==='*'||s.language===language)&&(!s.scheme||s.scheme==='file'));
    const visible=items.filter(x=>x.visible&&x.text&&(x.kind!=='language'||path&&matches(x.selector))).sort((a,b)=>(b.priority||0)-(a.priority||0));
    const signature=JSON.stringify(visible);if(signature===this.statusSignature)return;this.statusSignature=signature;
    if(!this.statusRoot){this.statusRoot=document.createElement('div');this.statusRoot.className='extension-status-items';document.querySelector('.status-spacer').after(this.statusRoot);}
    this.statusRoot.replaceChildren();
    for(const item of visible){
      const b=document.createElement('button');b.className='status-item extension-status-item';b.dataset.severity=item.severity||0;
      b.textContent=item.text.replace(/\$\(([^)]+)\)/g,(_,name)=>({check:'✓','check-all':'✓','alert':'!','warning':'!',error:'×','sync~spin':'↻'})[name]||'');
      b.title=[item.name||item.extension,typeof item.tooltip==='string'?item.tooltip:item.tooltip?.value,item.detail,item.busy?'En curso':''].filter(Boolean).join('\n');b.setAttribute('aria-label',b.title);
      b.onclick=()=>{const command=item.command,id=typeof command==='string'?command:command?.command;if(id)this.host.platform.safe(()=>this.host.platform.pluginCommand(item.extension+':'+id,command?.arguments||[]));};this.statusRoot.append(b);
    }
  }
  async syncEditors(){
    const h=this.host,ed=h.editor;if(ed.kind!=='monaco'||!document.hasFocus()||!(h.isTrusted?.()??h.service?.().trusted))return;
    const covered=document.documentElement.dataset.editorCovered==='true',editors=[];
    const pos=(line,column)=>({line:line-1,character:column-1});
    if(!covered)for(const [index,pane] of (ed.panes||[]).entries()){
      const view=pane.view,model=view?.getModel(),path=ed.pathFor(model);if(!path||path.startsWith('.team/')||!pane.node.getClientRects().length)continue;
      const opts=model.getOptions();editors.push({id:String(index),path,version:model.getVersionId(),language:model.getLanguageId(),active:view===ed.view,
        visibleRanges:view.getVisibleRanges().map(r=>({start:pos(r.startLineNumber,r.startColumn),end:pos(r.endLineNumber,r.endColumn)})),
        selections:view.getSelections().map(s=>({anchor:pos(s.selectionStartLineNumber,s.selectionStartColumn),active:pos(s.positionLineNumber,s.positionColumn)})),options:{tabSize:opts.tabSize,insertSpaces:opts.insertSpaces}});
    }
    const tabs=ed.visiblePaths().filter(path=>!path.startsWith('.team/')).map(path=>({path,column:(editors.findIndex(e=>e.path===path)+1)||1,active:ed.current===path,dirty:ed.isDirty(path)}));const key=JSON.stringify({editors,tabs});if(key===this.editorKey&&Date.now()-this.editorSent<1500)return;
    await h.platform.api('/extensions/editor-state',{editors,tabs,owner:this.owner});this.editorKey=key;this.editorSent=Date.now();
  }
  syncTerminalLinks(){
    this.terminalRegistrations ||= new Map();const hosts=this.terminalLinkHosts||[],signature=hosts.map(x=>x.id).join(','),wanted=new Set();
    for(const terminal of this.host.platform.terminals.values()){
      if(!terminal.xterm?.registerLinkProvider||terminal.closed||!hosts.length)continue;wanted.add(terminal.id);const old=this.terminalRegistrations.get(terminal.id);if(old?.signature===signature)continue;old?.provider.dispose();
      const provider=terminal.xterm.registerLinkProvider({provideLinks:(y,callback)=>{
        const buffer=terminal.xterm.buffer.active.getLine(y-1),line=buffer?.translateToString(true)||'';if(!line){callback(undefined);return;}
        Promise.allSettled(hosts.map(async ext=>{const result=await this.host.platform.api('/extensions/runtime/request',{id:ext.id,method:'terminalLinks',terminal:terminal.id,line});return (result.items||[]).map(link=>{
          const cell=offset=>{let units=0;for(let column=0;column<buffer.length;column++){if(units>=offset)return column+1;units+=buffer.getCell(column)?.getChars().length||0;}return buffer.length;};
          return {text:line.slice(link.startIndex,link.startIndex+link.length),range:{start:{x:cell(link.startIndex),y},end:{x:Math.max(1,cell(link.startIndex+link.length)-1),y}},activate:()=>this.host.platform.safe(async()=>{const data=await this.host.platform.api('/extensions/runtime/request',{id:ext.id,method:'terminalLink',link:link.id});for(const effect of data.effects||[]){if(effect.open)await this.host.openFile(effect.open);if(effect.message)this.host.notify(effect.message);if(effect.url){const url=new URL(effect.url);if(['https:','http:'].includes(url.protocol))window.open(url.href,'_blank','noopener,noreferrer');}}})};
        });})).then(results=>callback(results.flatMap(r=>r.status==='fulfilled'?r.value:[])));
      }});this.terminalRegistrations.set(terminal.id,{provider,signature});
    }
    for(const [id,value] of this.terminalRegistrations)if(!wanted.has(id)){value.provider.dispose();this.terminalRegistrations.delete(id);}
  }
  restoreTabs(){for(const state of this.panels.values())if(state.tab&&!state.tab.isConnected)document.getElementById('file-tabs').append(state.tab);}
  title(state){if(state.tab)state.tab.querySelector('span').textContent=state.panel.title;if(state.node)state.node.querySelector('strong').textContent=state.panel.title;}
  hide(){for(const state of this.panels.values()){if(state.node){state.node.hidden=true;state.node.classList.remove('active');}state.tab?.classList.remove('active');}if(!this.host.platform.page)delete document.documentElement.dataset.editorCovered;}
  remove(state){state.node?.remove();state.tab?.remove();for(const url of state.urls)URL.revokeObjectURL(url);if(state.node?.classList.contains('active'))this.host.platform.closePage();}
  async render(state){
    const h=this.host,p=state.panel;
    if(!state.tab){const tab=document.createElement('button');tab.className='file-tab extension-webview-tab';tab.innerHTML=icon('browser')+'<span></span>';tab.onclick=()=>this.show(state);document.getElementById('file-tabs').append(tab);state.tab=tab;}
    const active=state.node?.classList.contains('active');state.tab.querySelector('span').textContent=p.title;state.node?.remove();for(const url of state.urls)URL.revokeObjectURL(url);state.urls=[];
    const node=document.createElement('section');node.className='extension-webview-surface';node.hidden=!active;node.classList.toggle('active',!!active);node.dataset.panel=p.id;
    const header=document.createElement('header');header.innerHTML=`<strong>${esc(p.title)}</strong><span>${esc(p.extension)}</span><button class="icon-button" aria-label="Cerrar panel de extensión">${icon('close')}</button>`;header.querySelector('button').onclick=()=>h.platform.api('/extensions/runtime/request',{id:p.extension,method:'webviewDispose',panel:p.id}).catch(error=>h.notify(error.message,'error'));node.append(header);
    const frame=document.createElement('iframe');frame.title=p.title;frame.setAttribute('sandbox',p.options?.enableScripts?'allow-scripts allow-forms allow-downloads':'allow-forms');node.append(frame);state.node=node;state.frame=frame;state.loaded=false;
    // An opaque sandbox cannot load blobs created in the parent origin. The
    // backend gives this document a revocable, root-scoped resource capability.
    const html=p.html;
    const nonce=html.match(/nonce=["']([^"']+)["']/)?.[1]||'';
    const script=`<script${nonce?' nonce="'+esc(nonce)+'"':''}>const __stateKey=${JSON.stringify(p.id)};let __state=${JSON.stringify(state.savedState??p.state??null).replaceAll('<','\\u003c')},__acquired=false;window.acquireVsCodeApi=()=>{if(__acquired)throw Error('acquireVsCodeApi ya se ha llamado.');__acquired=true;return Object.freeze({postMessage:message=>parent.postMessage({zenitWebview:__stateKey,message},'*'),getState:()=>__state,setState:value=>{__state=value;parent.postMessage({zenitWebview:__stateKey,state:value,stateUpdate:true},'*');return value;}});};<\/script>`;
    frame.onload=()=>{state.loaded=true;};const rendered=await h.platform.api('/extensions/webview/document',{panel:p.id,html:script+html});frame.src=rendered.url;
    document.getElementById('editor-panel').append(node);this.layout();
  }
  show(state){for(const value of this.panels.values()){if(value.node){value.node.hidden=true;value.node.classList.remove('active');}value.tab?.classList.remove('active');}this.host.platform.closePage();state.node.hidden=false;state.node.classList.add('active');state.tab.classList.add('active');document.documentElement.dataset.editorCovered='true';}
  async receive(event){const id=event.data?.zenitWebview,state=this.panels.get(id);if(!state||event.source!==state.frame?.contentWindow)return;if(event.data.stateUpdate){state.savedState=event.data.state;return;}try{await this.host.platform.api('/extensions/runtime/request',{id:state.panel.extension,method:'webviewMessage',panel:id,message:event.data.message});}catch(error){this.host.notify(error.message,'error');}}
  dispose(){this.disposed=true;this.editorDecorations?.dispose();for(const value of this.terminalRegistrations?.values()||[])value.provider.dispose();this.outputUI.dispose();this.quickinput.dispose();clearTimeout(this.timer);this.resize.disconnect();window.removeEventListener('message',this.message);for(const state of this.panels.values())this.remove(state);}
}
