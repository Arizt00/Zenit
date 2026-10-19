import {icon,escapeHTML as esc} from './icons.js';
import {hoverReveal} from './hover-reveal.js';
import {teamIntro} from './team-view.js';
import {CoCoProjectUI} from './team-project.js';
import {SharedExecutions} from '../team-execution.js';
import {CoCoDrafts} from '../coco-drafts.js';

/** Peers keep their own CRDT state and send only missing changes. */
export class TeamUI {
  constructor(host){this.host=host;this.project=new CoCoProjectUI(this);this.files=new Map();this.pending=new Map();this.runIntents=new Map();this.executions=new SharedExecutions(body=>this.api('/request',body));this.peer=crypto.randomUUID();this.running=false;this.applying=false;this.errors=0;this.pollTimer=0;this.requestQueue=Promise.resolve();this.name=host.platform.host.studio?.profile.displayName||'Programador';this.key=e=>{if(!(e.ctrlKey||e.metaKey)||e.altKey||e.key.toLowerCase()!=='z'||!e.target.closest?.('.monaco-editor'))return;const entry=this.files.get(host.editor.current);if(!this.running||!entry||this.snapshot?.self?.permissions?.edit===false)return;e.preventDefault();e.stopImmediatePropagation();e.shiftKey?entry.undo.redo():entry.undo.undo();};document.addEventListener('keydown',this.key,true);}
  api(path,body){return this.host.platform.api('/team'+path,body);}
  async open(){
    const status=await this.api('');this.state=status;
    this.host.modal('Co-Code',`<section class="team-workbench"><header><span class="team-mark">${icon('coco')}</span><div><h3>CoCo. Un código, muchas perspectivas.</h3><p>Edición simultánea y un entorno de ejecución en el equipo anfitrión.</p></div></header>${teamIntro(this.name,this.host.editor.current,status.active)}<div class="team-live" data-team-active ${status.active?'':'hidden'}><label>Invitación<input data-team-link readonly value="${esc(status.invitation||'')}"></label><div class="team-copy-actions"><button class="secondary-button" data-team-copy title="Copiar invitación">${icon('copy')}<span>Copiar invitación</span></button></div><div class="team-connection" role="status"></div><button class="secondary-button" data-team-retry hidden>Reintentar conexión de Internet</button><p class="team-environment"></p><div class="team-peers" aria-label="Participantes"></div><div class="team-files"></div><div class="team-tools"><button class="secondary-button" data-team-share>${icon('plus')}Compartir archivo actual</button><button class="secondary-button" data-team-save>${icon('check')}Guardar compartido</button><button class="secondary-button" data-team-execute>${icon('play')}Ejecutar en el anfitrión</button><button class="secondary-button" data-team-undo>${icon('undo')}Deshacer mi último cambio</button><button class="text-button" data-team-leave>Terminar conexión</button></div><details class="team-review"><summary>Puntos de control y revisión</summary><div class="team-tools"><button class="secondary-button" data-team-checkpoint>Guardar punto compartido</button><button class="secondary-button" data-team-review>Revisar cambios con Melody</button></div><div class="team-checkpoints"></div></details><pre class="team-output" tabindex="0" aria-label="Salida compartida"></pre></div><details class="team-connectors"><summary>Conectar desde otra IDE</summary><p>VS Code y editores compatibles: instala el VSIX y ejecuta «Co-Code: unirme». En JetBrains, instala el ZIP y abre la herramienta Co-Code; utiliza el editor compartido integrado.</p><div class="team-tools"><button class="secondary-button" data-team-connector="vscode">Descargar VSIX</button><button class="secondary-button" data-team-connector="jetbrains">Descargar para JetBrains</button></div></details><p role="status" class="team-status"></p><footer>La invitación da acceso a los archivos compartidos. No hay límite fijo de participantes; la capacidad depende del anfitrión y de la red. Red local conecta directamente; Internet usa una dirección HTTPS temporal de Cloudflare. Los participantes comparten esta misma sesión y el entorno del anfitrión.</footer></section>`,{wide:true});
    this.root=document.querySelector('.team-workbench');const safe=fn=>this.host.platform.safe(fn),root=this.root;this.project.mount(root);
    for(const tab of root.querySelectorAll('[data-team-entry]'))tab.onclick=()=>{for(const item of root.querySelectorAll('[data-team-entry]'))item.setAttribute('aria-selected',String(item===tab));for(const panel of root.querySelectorAll('[data-team-entry-panel]'))panel.hidden=panel.dataset.teamEntryPanel!==tab.dataset.teamEntry;};
    root.querySelector('.team-entry-tabs').onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...root.querySelectorAll('[data-team-entry]')],next=e.key==='Home'?tabs[0]:e.key==='End'?tabs[1]:tabs.find(t=>t.getAttribute('aria-selected')!=='true');next.click();next.focus();};
    root.querySelector('[data-team-host]').onclick=()=>safe(async()=>{if(!await this.host.ensureTrust())return;const path=this.host.editor.current,record=this.host.editor.models.get(path);const shareProject=root.querySelector('[data-team-project]').checked;if((!record||record.kind==='binary')&&!shareProject)throw Error('Abre un archivo de texto o comparte el árbol del proyecto.');this.name=root.querySelector('[data-team-name]').value.trim()||this.name;this.state=await this.api('/start',{protocol:2,shareProject,documents:record&&record.kind!=='binary'?[{path,text:this.host.editor.getValue()}]:[],mode:root.querySelector('[data-team-mode]:checked').value,allowRun:root.querySelector('[data-team-run]').checked});await this.connect();await this.open();});
    for(const input of root.querySelectorAll('[data-team-mode]'))input.onchange=()=>root.querySelector('[data-team-internet-info]').hidden=root.querySelector('[data-team-mode]:checked').value!=='internet';root.querySelector('[data-team-retry]').onclick=()=>safe(async()=>{await this.api('/internet',{});this.state=await this.api('');this.paint();});
    root.querySelector('[data-team-join]').onclick=()=>safe(async()=>{if(!await this.host.ensureTrust())return;this.name=root.querySelector('[data-team-name]').value.trim()||this.name;this.state=await this.api('/join',{invitation:root.querySelector('[data-team-invite]').value.trim()});await this.connect();await this.open();});
    hoverReveal(root.querySelector('[data-team-copy]'));root.querySelector('[data-team-copy]').onclick=()=>safe(()=>navigator.clipboard.writeText(this.state.invitation));root.querySelector('[data-team-leave]').onclick=()=>safe(async()=>{await this.stop();await this.open();});
    root.querySelector('[data-team-share]').onclick=()=>safe(async()=>{const path=this.host.editor.current,record=this.host.editor.models.get(path);if(!record||record.kind==='binary')throw Error('Abre un archivo de texto para compartirlo.');await this.api('/request',{action:'share',documents:[{path,text:this.host.editor.getValue()}]});await this.sync();});
    root.querySelector('[data-team-save]').onclick=()=>safe(()=>this.save(this.host.editor.current));root.querySelector('[data-team-execute]').onclick=()=>safe(()=>this.run(this.host.editor.current));root.querySelector('[data-team-undo]').onclick=()=>{this.files.get(this.host.editor.current)?.undo.undo();};
    root.querySelector('[data-team-checkpoint]').onclick=()=>safe(async()=>{await this.flush();await this.api('/request',{action:'checkpoint',label:this.name+' · '+new Date().toLocaleTimeString()});await this.sync();});
    root.querySelector('[data-team-review]').onclick=()=>safe(()=>this.project.review());
    for(const button of root.querySelectorAll('[data-team-connector]'))button.onclick=()=>safe(async()=>{const result=await this.api('/connector?target='+button.dataset.teamConnector),blob=new Blob([this.decode(result.data)],{type:'application/octet-stream'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=result.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);this.status('Conector preparado · SHA-256 '+result.sha256);});
    if(status.active){if(!this.running)await this.connect();this.paint();}
  }
  async connect(){
    if(this.room&&this.room!==this.state.room)this.disposeFiles();
    this.Y ||= await import('/team-vendor/yjs.mjs');this.running=true;this.generation=(this.generation||0)+1;this.room=this.state.room;await this.sync();
  }
  owns(path){return this.running&&this.files.has(path);}
  async sync(){
    clearTimeout(this.pollTimer);if(!this.running||this.busy)return;this.busy=true;const generation=this.generation,sent=this.snapshot?.self?.permissions?.edit===false?new Map():this.pending;if(sent===this.pending)this.pending=new Map();
    try{
      const Y=this.Y,vectors={};for(const entry of this.files.values())vectors[entry.path]=this.encode(Y.encodeStateVector(entry.doc));
      const active=this.files.get(this.host.editor.current),cursor=this.host.editor.view?.getPosition?.();
      const response=await this.api('/request',{action:'sync',peer:this.peer,name:this.name,path:active?.path||'',cursor,vectors,treeVersion:this.project.treeVersion,documentIds:Object.fromEntries([...this.files.values()].filter(e=>e.id).map(e=>[e.path,e.id])),updates:Object.fromEntries([...sent].map(([path,updates])=>[path,this.encode(Y.mergeUpdates(updates))]))});
      if(!this.running||generation!==this.generation)return;this.room=response.room;this.snapshot=response;this.project.receive(response,sent);this.drafts||=new CoCoDrafts(Y,response.room);this.errors=0;if(response.connection){this.state.connection=response.connection;this.state.invitation=response.invitation;}
      for(const [path,value] of Object.entries(response.updates)){
        const local=this.state.hosting?path:'.team/'+response.room+'/'+path,id=this.project.metadata.get(path);let entry=(id?[...this.files.values()].find(e=>e.id===id):null)||this.files.get(local);
        let fresh=false;if(!entry){fresh=true;const doc=new Y.Doc();entry={path,local,id:this.project.metadata.get(path),doc,text:doc.getText('text'),listeners:[]};this.files.set(local,entry);entry.undo=new Y.UndoManager(entry.text,{trackedOrigins:new Set(['local'])});doc.on('update',(update,origin)=>{if(origin==='remote')return;const path=entry.path;if(!this.pending.has(path))this.pending.set(path,[]);this.pending.get(path).push(update);this.drafts.schedule(entry.id||entry.path,doc);this.schedule(60);});}
        Y.applyUpdate(entry.doc,this.decode(value),'remote');entry.seed??=entry.text.toString();if(fresh)await this.drafts.restore(entry.id||entry.path,entry.doc);this.bind(entry);
      }
      const selected=this.files.get(this.host.editor.current),execution=selected?await this.executions.read(selected.path,response.executions?.[selected.path]):null;if(!this.running||generation!==this.generation)return;this.output=execution?.text||'';
      this.paint();
    }catch(error){if(!this.running||generation!==this.generation)return;for(const [path,updates] of sent)this.pending.set(path,[...updates,...(this.pending.get(path)||[])]);this.errors++;this.lastError=error.message;this.status('Conexión pendiente. Tus cambios se conservan localmente. '+error.message);}
    finally{this.busy=false;this.schedule(this.errors?Math.min(8000,500*2**this.errors):this.pending.size&&this.snapshot?.self?.permissions?.edit!==false?60:document.hidden?1800:450);}
  }
  bind(entry){
    const ed=this.host.editor;let record=ed.models.get(entry.local);const value=entry.text.toString();
    if(!record){ed.open({path:entry.local,content:value,revision:null},{activate:this.files.size===1});record=ed.models.get(entry.local);}
    record.teamReadOnly=this.snapshot?.self?.permissions?.edit===false;for(const pane of ed.panes||[])if(pane.view?.getModel()===record.model)pane.view.updateOptions({readOnly:record.teamReadOnly});
    if(entry.model===record.model)return;
    for(const listener of entry.listeners)listener.dispose();entry.listeners=[];entry.model=record.model;
    if(!record.model)throw Error('La edición en equipo requiere el motor de editor integrado.');
    // Existing host text seeded the server; joining buffers have their own namespace.
    this.applying=true;try{if(record.model.getValue()!==value)record.model.setValue(value);}finally{this.applying=false;}
    if(entry.observer)entry.text.unobserve(entry.observer);
    entry.observer=event=>{if(event.transaction.origin==='local')return;const model=entry.model;if(model.isDisposed())return;let offset=0;const edits=[];for(const delta of event.delta){if(delta.retain)offset+=delta.retain;if(delta.delete){const a=model.getPositionAt(offset),b=model.getPositionAt(offset+delta.delete);edits.push({range:new monaco.Range(a.lineNumber,a.column,b.lineNumber,b.column),text:''});offset+=delta.delete;}if(delta.insert){const p=model.getPositionAt(offset);edits.push({range:new monaco.Range(p.lineNumber,p.column,p.lineNumber,p.column),text:String(delta.insert)});}}this.applying=true;try{model.applyEdits(edits);}finally{this.applying=false;}};
    entry.text.observe(entry.observer);
    entry.listeners.push(record.model.onDidChangeContent(event=>{if(this.applying)return;entry.doc.transact(()=>{for(const change of [...event.changes].sort((a,b)=>b.rangeOffset-a.rangeOffset)){if(change.rangeLength)entry.text.delete(change.rangeOffset,change.rangeLength);if(change.text)entry.text.insert(change.rangeOffset,change.text);}},'local');}));
  }
  schedule(delay){clearTimeout(this.pollTimer);if(this.running)this.pollTimer=setTimeout(()=>this.sync(),delay);}
  encode(bytes){let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);}
  decode(value){return Uint8Array.from(atob(value),c=>c.charCodeAt(0));}
  async flush(){while(this.busy)await new Promise(resolve=>setTimeout(resolve,20));await this.sync();if(this.errors||this.pending.size)throw Error('No se ha confirmado la sincronización. Se conserva el búfer.');}
  async save(local){const entry=this.files.get(local);if(!entry)throw Error('Selecciona un archivo del equipo.');await this.flush();const result=await this.api('/request',{action:'save',path:entry.path});const record=this.host.editor.models.get(local);record.savedValue=result.text;record.revision=result.revision;this.host.editor.callbacks.change?.(local,this.host.editor.isDirty(local));this.status('Guardado en el anfitrión: '+entry.path);return {...result,path:local};}
  async run(local){
    const entry=this.files.get(local);if(!entry)throw Error('Selecciona un archivo del equipo.');
    let intent=this.runIntents.get(local);if(intent?.promise)return intent.promise;
    if(!intent){intent={requestId:this.peer+':'+crypto.randomUUID()};this.runIntents.set(local,intent);}
    let acknowledged=false;const room=this.room;
    intent.promise=(async()=>{
      await this.flush();const result=await this.api('/request',{action:'run',path:entry.path,requestId:intent.requestId});acknowledged=true;this.job=result.job;
      while(this.running&&this.room===room){const data=await this.executions.read(entry.path,result);if(this.host.editor.current===local){this.output=data.text;this.paint();}if(data.done){this.status('Ejecución terminada · código '+data.code);break;}await new Promise(resolve=>setTimeout(resolve,250));}
    })();
    try{return await intent.promise;}finally{intent.promise=null;if(acknowledged)this.runIntents.delete(local);}
  }
  status(text){if(this.root?.isConnected)this.root.querySelector('.team-status').textContent=text;}
  paint(){
    const root=this.root;if(!root?.isConnected||!this.snapshot)return;const s=this.snapshot;
    const connection=this.state.connection||{},ready=connection.phase==='ready',link=root.querySelector('[data-team-link]');if(link.value!==(this.state.invitation||''))link.value=this.state.invitation||'';link.placeholder=ready?'Invitación':'Preparando conexión de estaciones…';root.querySelector('[data-team-copy]').disabled=!this.state.invitation;root.querySelector('[data-team-retry]').hidden=connection.kind!=='internet'||connection.phase!=='failed';root.querySelector('.team-connection').textContent=connection.error||(ready?(connection.kind==='internet'?'Internet · HTTPS · '+(connection.provider||'Estación remota'):connection.kind==='lan'?'Red local · conexión entre estaciones':'Este equipo · sesión compartida'):'Preparando la conexión HTTPS…');
    root.querySelector('.team-environment').textContent='Estación anfitriona: '+s.environment.host+' · '+s.environment.workspace+' · '+s.environment.runtime;
    const peers=root.querySelector('.team-peers'),peerSignature=JSON.stringify(s.peers);if(peers.dataset.signature!==peerSignature){peers.dataset.signature=peerSignature;peers.innerHTML=s.peers.map(p=>`<span>${icon('person')}<strong>${esc(p.name)}</strong><small>${esc(p.station||'')}${p.station&&p.path?' · ':''}${esc(p.path)}</small></span>`).join('');}
    const list=root.querySelector('.team-files'),fileSignature=JSON.stringify([...this.files.keys()]);if(list.dataset.signature!==fileSignature){list.dataset.signature=fileSignature;list.replaceChildren();for(const [local,entry] of this.files){const button=document.createElement('button');button.className='secondary-button';button.textContent=entry.path;button.onclick=()=>{this.bind(entry);this.host.editor.activate(local);this.host.closeModal();};list.append(button);}}
    const checkpointList=root.querySelector('.team-checkpoints'),signature=JSON.stringify(s.checkpoints);if(checkpointList.dataset.signature!==signature){checkpointList.dataset.signature=signature;checkpointList.replaceChildren();for(const item of s.checkpoints||[]){const button=document.createElement('button');button.className='secondary-button';button.textContent=item.label;button.disabled=!this.state.hosting;button.title='Restaurar este punto sin escribir en disco';button.onclick=()=>this.host.platform.safe(async()=>{await this.flush();await this.api('/request',{action:'restore',id:item.id});await this.sync();});checkpointList.append(button);}}
    root.querySelector('[data-team-share]').hidden=!this.state.hosting;root.querySelector('[data-team-share]').disabled=this.files.has(this.host.editor.current);
    root.querySelector('[data-team-save]').disabled=!this.state.hosting&&!s.allowRun;root.querySelector('[data-team-execute]').disabled=!s.allowRun;root.querySelector('.team-output').textContent=this.output||'La salida de ejecución aparecerá aquí.';this.project.paint(s);
  }
  async review(){
    await this.flush();const changes=[...this.files.values()].filter(e=>e.seed!==e.text.toString()).map(e=>({file:e.path,before:e.seed,after:e.text.toString()}));if(!changes.length){this.status('No hay cambios desde que te uniste.');return;}
    const question='Revisa los cambios de esta sesión compartida. Explica los efectos, posibles conflictos y pruebas necesarias. No atribuyas líneas a una persona sin evidencia ni afirmes que se han ejecutado pruebas.\n'+JSON.stringify(changes).slice(0,60000);
    this.host.closeModal();this.host.platform.host.studio.host.dock.show('assistant');this.host.platform.setMelodyMode?.('chat');document.getElementById('ai-input').value=question;await this.host.platform.sendAI(question,{consult:true});
  }
  async stop(){this.generation++;this.running=false;clearTimeout(this.pollTimer);await this.api('/stop',{});this.disposeFiles();}
  disposeFiles(){this.drafts?.flushAll();this.drafts=null;this.project.release();for(const entry of this.files.values()){entry.listeners.forEach(x=>x.dispose());entry.undo.destroy();entry.doc.destroy();}this.files.clear();this.pending.clear();this.executions.clear();this.runIntents.clear();}
  dispose(){document.removeEventListener('keydown',this.key,true);this.generation++;this.running=false;clearTimeout(this.pollTimer);this.disposeFiles();}
}
