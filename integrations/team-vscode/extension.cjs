const v=require('vscode'),Y=require('./vendor/yjs.cjs'),crypto=require('node:crypto'),http=require('node:http'),https=require('node:https');
let active;
class Client {
  constructor(invite,name){const u=new URL(invite);if(!['http:','https:'].includes(u.protocol)||!u.hash||u.username)throw Error('Invitación no válida.');this.key=u.hash.slice(1);u.hash='';u.pathname='/v1';this.url=u;this.name=name;this.peer=crypto.randomUUID();this.resumeKey=crypto.randomBytes(32).toString('hex');this.files=new Map();this.pending=new Map();this.output=v.window.createOutputChannel('Co-Code · Zénit');this.disposables=[];this.stopped=false;this.applying=false;this.serial=Promise.resolve();this.executions=new Map();this.runIntents=new Map();}
  async restoreCredentials(context,invite){
    this.credentials=context.secrets;this.state=context.workspaceState;
    this.credentialKey='coco-room:'+crypto.createHash('sha256').update(this.key).digest('hex');
    const legacy='coco:'+crypto.createHash('sha256').update(invite).digest('hex');
    try{const previous=JSON.parse(await this.credentials.get(this.credentialKey)||await this.credentials.get(legacy));if(typeof previous?.peer==='string'&&typeof previous?.resumeKey==='string'){this.peer=previous.peer;this.resumeKey=previous.resumeKey;}}catch{}
    if(this.state.get(this.credentialKey+':intents')===undefined){const old=this.state.get(legacy+':intents');if(old)await this.state.update(this.credentialKey+':intents',old);}
  }
  send(body){return new Promise((resolve,reject)=>{const raw=Buffer.from(JSON.stringify(body)),request=(this.url.protocol==='https:'?https:http).request(this.url,{method:'POST',headers:{Authorization:'Bearer '+this.key,'Content-Type':'application/json','Content-Length':raw.length},timeout:8000},response=>{let data='';response.setEncoding('utf8');response.on('data',chunk=>{data+=chunk;if(data.length>32000000){response.destroy();reject(Error('Respuesta demasiado grande.'));}});response.on('end',()=>{try{const value=JSON.parse(data);if(response.statusCode!==200)throw Object.assign(Error(value.error||'Conexión rechazada.'),{status:response.statusCode});resolve(value);}catch(error){reject(error);}});});request.on('error',reject);request.on('timeout',()=>request.destroy(Error('El anfitrión no respondió.')));request.end(raw);});}
  async request(body){body={...body,peer:this.peer,resumeKey:this.resumeKey};try{return await this.send(body);}catch(error){if(this.stopped||!(body.action==='run'&&body.requestId||body.action==='sync'&&body.resumeKey||['project-create','project-rename'].includes(body.action)&&body.operationId)||error.status)throw error;return this.send(body);}}
  async start(){
    for(const [key,requestId] of Object.entries(this.state?.get(this.credentialKey+':intents',{})||{}).slice(-128))if(typeof requestId==='string'&&requestId.length<=120)this.runIntents.set(key,{requestId});
    if(this.credentials&&this.resumeKey){await this.credentials.store(this.credentialKey,JSON.stringify({peer:this.peer,resumeKey:this.resumeKey}));this.credentialsSaved=true;}
    const changed=new v.EventEmitter(),entryFor=uri=>[...this.files.values()].find(e=>e.uri?.toString()===uri.toString());this.changed=changed;
    const denied=()=>{throw v.FileSystemError.NoPermissions('Los archivos los administra el anfitrión.');};
    this.disposables.push(changed,v.workspace.registerFileSystemProvider('zenit-team',{
      onDidChangeFile:changed.event,watch:()=>new v.Disposable(()=>{}),stat:uri=>{const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);return {type:v.FileType.File,ctime:0,mtime:0,size:Buffer.byteLength(e.text.toString()),permissions:this.permissions?.edit===false?(v.FilePermission?.Readonly||1):undefined};},
      readDirectory:()=>[...this.files.values()].map(e=>[e.path,v.FileType.File]),readFile:uri=>{const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);return Buffer.from(e.text.toString());},
      writeFile:async(uri,bytes)=>{if(this.permissions?.save===false)throw v.FileSystemError.NoPermissions('El anfitrión no ha concedido guardar.');const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);if(Buffer.from(bytes).toString('utf8')!==e.text.toString())throw v.FileSystemError.Unavailable('El búfer está cambiando. Vuelve a guardar.');await this.sync();await this.request({action:'save',path:e.path});},rename:denied,delete:denied,createDirectory:denied
    },{isCaseSensitive:true}));
    this.disposables.push(v.workspace.onDidChangeTextDocument(event=>{const entry=[...this.files.values()].find(e=>e.doc===event.document);if(!entry||this.applying)return;entry.crdt.transact(()=>{for(const edit of [...event.contentChanges].sort((a,b)=>b.rangeOffset-a.rangeOffset)){if(edit.rangeLength)entry.text.delete(edit.rangeOffset,edit.rangeLength);if(edit.text)entry.text.insert(edit.rangeOffset,edit.text);}},'local');}));
    await this.sync();for(const entry of this.files.values())await v.window.showTextDocument(entry.doc);this.timer=setInterval(()=>this.sync().catch(e=>this.output.appendLine(e.message)),500);
  }
  sync(){const operation=this.serial.catch(()=>{}).then(()=>this.performSync());this.serial=operation;return operation;}
  async performSync(){
    if(this.stopped)return;const sent=this.permissions?.edit===false?new Map():this.pending;if(sent===this.pending)this.pending=new Map();
    try{const result=await this.request({action:'sync',name:this.name,station:'VS Code · CoCo',treeVersion:this.treeVersion,documentIds:Object.fromEntries([...this.files].map(([path,e])=>[path,e.id])),vectors:Object.fromEntries([...this.files].map(([path,e])=>[path,Buffer.from(Y.encodeStateVector(e.crdt)).toString('base64')])),updates:Object.fromEntries([...sent].map(([path,updates])=>[path,Buffer.from(Y.mergeUpdates(updates)).toString('base64')]))});
      this.resumeKey=result.self?.resumeKey||this.resumeKey;const beforePermissions=JSON.stringify(this.permissions);this.permissions=result.self?.permissions||{edit:true,save:result.allowRun,run:result.allowRun};this.allowRun=this.permissions.run;if(result.project?.files)this.tree=result.project.files;this.treeVersion=result.project?.version;if(beforePermissions!==JSON.stringify(this.permissions))this.changed?.fire([...this.files.values()].filter(e=>e.uri).map(e=>({type:v.FileChangeType.Changed,uri:e.uri})));
      if(result.acceptedUpdates===false)for(const [path,updates] of sent)this.pending.set(path,[...updates,...this.pending.get(path)||[]]);
      if(this.credentials&&this.resumeKey&&!this.credentialsSaved){await this.credentials.store(this.credentialKey,JSON.stringify({peer:this.peer,resumeKey:this.resumeKey}));this.credentialsSaved=true;}
      for(const item of result.documents||[]){const e=[...this.files.values()].find(e=>e.id===item.id);if(!e||e.path===item.path)continue;const old=e.path;this.files.delete(old);e.path=item.path;this.files.set(item.path,e);if(this.pending.has(old)){this.pending.set(item.path,[...this.pending.get(old),...this.pending.get(item.path)||[]]);this.pending.delete(old);}this.output.appendLine('Renombrado: '+old+' → '+item.path);}
      for(const [path,update] of Object.entries(result.updates)){let entry=this.files.get(path);if(!entry){const crdt=new Y.Doc();entry={id:result.documents?.find(d=>d.path===path)?.id||path,path,crdt,text:crdt.getText('text')};entry.undo=new Y.UndoManager(entry.text,{trackedOrigins:new Set(['local'])});this.files.set(path,entry);crdt.on('update',(update,origin)=>{if(origin==='remote')return;const path=entry.path;if(!this.pending.has(path))this.pending.set(path,[]);this.pending.get(path).push(update);});}
        Y.applyUpdate(entry.crdt,Buffer.from(update,'base64'),'remote');const text=entry.text.toString();if(!entry.doc){entry.path=path;entry.uri=v.Uri.from({scheme:'zenit-team',authority:result.room,path:'/'+path});entry.doc=await v.workspace.openTextDocument(entry.uri);await v.languages.setTextDocumentLanguage(entry.doc,this.language(path));}
        else if(entry.doc.getText()!==text){const before=entry.doc.getText();let start=0,end=0;while(start<before.length&&start<text.length&&before[start]===text[start])start++;while(end<before.length-start&&end<text.length-start&&before[before.length-1-end]===text[text.length-1-end])end++;const edit=new v.WorkspaceEdit();edit.replace(entry.doc.uri,new v.Range(entry.doc.positionAt(start),entry.doc.positionAt(before.length-end)),text.slice(start,text.length-end));this.applying=true;try{if(!await v.workspace.applyEdit(edit))throw Error('El editor rechazó una actualización.');}finally{this.applying=false;}}
      }
      const entry=[...this.files.values()].find(e=>e.doc===v.window.activeTextEditor?.document);if(entry)await this.pollExecution(entry.path,result.executions?.[entry.path]);
    }catch(error){for(const [path,updates] of sent)this.pending.set(path,[...updates,...this.pending.get(path)||[]]);throw error;}
  }
  language(path){const ext=path.split('.').at(-1);return {py:'python',c:'c',cpp:'cpp',h:'c',hpp:'cpp',java:'java',js:'javascript',ts:'typescript',nc:'nc',asm:'asm',json:'json',md:'markdown'}[ext]||'plaintext';}
  current(){const doc=v.window.activeTextEditor?.document;const entry=[...this.files.values()].find(e=>e.doc===doc);if(!entry)throw Error('Selecciona uno de los búferes compartidos.');return entry;}
  async save(){const entry=this.current();if(!await entry.doc.save())throw Error('No se pudo guardar el búfer compartido.');v.window.showInformationMessage('Guardado en el anfitrión: '+entry.path);}
  async pollExecution(path,run){
    if(!run||run.available===false)return null;
    let record=this.executions.get(path);
    if(record?.job!==run.job){record={job:run.job,offset:0,done:false};this.executions.set(path,record);this.output.appendLine('▶ '+path);}
    if(record.done)return record;if(record.pending)return record.pending;
    record.pending=(async()=>{const data=await this.request({action:'job',job:record.job,offset:record.offset});record.offset=data.offset;record.done=data.done&&!data.more;record.interrupted=Boolean(data.interrupted);this.output.append(data.output);if(record.done&&record.interrupted)this.output.appendLine('\nEjecución interrumpida. El anfitrión debe revisarla antes de iniciar otra.');return record;})();
    try{return await record.pending;}finally{record.pending=null;}
  }
  async run(){
    const entry=this.current(),intentKey=entry.id||entry.path;let intent=this.runIntents.get(intentKey);if(intent?.promise)return intent.promise;
    if(!intent){intent={requestId:this.peer+':'+crypto.randomUUID()};this.runIntents.set(intentKey,intent);}
    let acknowledged=false;
    intent.promise=(async()=>{await this.saveIntents();await this.sync();const result=await this.request({action:'run',path:entry.path,requestId:intent.requestId});acknowledged=true;this.output.show(true);while(!this.stopped){const data=await this.pollExecution(entry.path,result);if(data.done)break;await new Promise(resolve=>setTimeout(resolve,300));}})();
    try{return await intent.promise;}finally{intent.promise=null;if(acknowledged){this.runIntents.delete(intentKey);await this.saveIntents();}}
  }
  async saveIntents(){if(this.runIntents.size>128)throw Error('Reconecta antes de iniciar otras ejecuciones pendientes.');await this.state?.update(this.credentialKey+':intents',Object.fromEntries([...this.runIntents].map(([path,item])=>[path,item.requestId])));}
  async mutation(body){const key=JSON.stringify([body.action,body.path,body.newPath]);let intent=this.runIntents.get(key);if(!intent){intent={requestId:crypto.randomUUID()};this.runIntents.set(key,intent);}await this.saveIntents();const result=await this.request({...body,operationId:intent.requestId});this.runIntents.delete(key);await this.saveIntents();return result;}
  async undo(){if(this.permissions?.edit===false)throw Error('La estación tiene permiso de lectura.');this.current().undo.undo();await this.sync();}
  async openProject(){const item=await v.window.showQuickPick((this.tree||[]).filter(f=>f.text).map(f=>({label:f.path})),{title:'CoCo · proyecto compartido'});if(!item)return;await this.request({action:'project-open',path:item.label});await this.sync();await v.window.showTextDocument(this.files.get(item.label).doc);}
  async createFile(){if(!this.permissions?.tree)throw Error('El anfitrión no ha concedido editar el árbol.');const path=await v.window.showInputBox({title:'CoCo · nuevo archivo',prompt:'Ruta relativa dentro del proyecto anfitrión'});if(!path)return;await this.mutation({action:'project-create',path});await this.sync();await v.window.showTextDocument(this.files.get(path).doc);}
  async renameFile(){if(!this.permissions?.tree)throw Error('El anfitrión no ha concedido editar el árbol.');const entry=this.current(),newPath=await v.window.showInputBox({title:'CoCo · renombrar archivo',value:entry.path});if(!newPath||newPath===entry.path)return;await this.sync();await this.mutation({action:'project-rename',path:entry.path,newPath});await this.sync();v.window.showInformationMessage('Documento compartido renombrado: '+newPath);}
  stop(){this.stopped=true;clearInterval(this.timer);this.request({action:'leave',peer:this.peer}).catch(()=>{});this.disposables.forEach(x=>x.dispose());for(const e of this.files.values()){e.undo.destroy();e.crdt.destroy();}this.output.dispose();}
}
exports.Client=Client;
exports.activate=context=>{
  const command=(name,fn)=>context.subscriptions.push(v.commands.registerCommand(name,async()=>{try{return await fn();}catch(e){v.window.showErrorMessage('Co-Code: '+e.message);}}));
  command('zenit.team.join',async()=>{const invite=await v.window.showInputBox({title:'Invitación de Zénit',prompt:'Accede a los documentos y al proyecto que comparta el anfitrión.',password:true});if(!invite)return;const name=await v.window.showInputBox({title:'Tu nombre',value:'Programador'});if(name===undefined)return;active?.stop();active=new Client(invite,name);await active.restoreCredentials(context,invite);await active.start();});
  command('zenit.team.openProject',()=>active?.openProject());command('zenit.team.createFile',()=>active?.createFile());command('zenit.team.renameFile',()=>active?.renameFile());
  command('zenit.team.leave',()=>{active?.stop();active=null;});command('zenit.team.save',()=>active?.save());command('zenit.team.run',()=>active?.run());command('zenit.team.undo',()=>active?.undo());context.subscriptions.push({dispose(){active?.stop();}});
};
exports.deactivate=()=>active?.stop();
