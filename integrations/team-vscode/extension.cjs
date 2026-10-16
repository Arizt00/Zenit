const v=require('vscode'),Y=require('./vendor/yjs.cjs'),crypto=require('node:crypto'),http=require('node:http'),https=require('node:https');
let active;
class Client {
  constructor(invite,name){const u=new URL(invite);if(!['http:','https:'].includes(u.protocol)||!u.hash||u.username)throw Error('Invitación no válida.');this.key=u.hash.slice(1);u.hash='';u.pathname='/v1';this.url=u;this.name=name;this.peer=crypto.randomUUID();this.files=new Map();this.pending=new Map();this.output=v.window.createOutputChannel('Co-Code · Zénit');this.disposables=[];this.stopped=false;this.applying=false;this.serial=Promise.resolve();}
  request(body){return new Promise((resolve,reject)=>{const raw=Buffer.from(JSON.stringify(body)),request=(this.url.protocol==='https:'?https:http).request(this.url,{method:'POST',headers:{Authorization:'Bearer '+this.key,'Content-Type':'application/json','Content-Length':raw.length},timeout:8000},response=>{let data='';response.setEncoding('utf8');response.on('data',chunk=>{data+=chunk;if(data.length>8000000){response.destroy();reject(Error('Respuesta demasiado grande.'));}});response.on('end',()=>{try{const value=JSON.parse(data);if(response.statusCode!==200)throw Error(value.error||'Conexión rechazada.');resolve(value);}catch(error){reject(error);}});});request.on('error',reject);request.on('timeout',()=>request.destroy(Error('El anfitrión no respondió.')));request.end(raw);});}
  async start(){
    const changed=new v.EventEmitter(),entryFor=uri=>[...this.files.values()].find(e=>e.uri?.toString()===uri.toString());
    const denied=()=>{throw v.FileSystemError.NoPermissions('Los archivos los administra el anfitrión.');};
    this.disposables.push(changed,v.workspace.registerFileSystemProvider('zenit-team',{
      onDidChangeFile:changed.event,watch:()=>new v.Disposable(()=>{}),stat:uri=>{const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);return {type:v.FileType.File,ctime:0,mtime:0,size:Buffer.byteLength(e.text.toString())};},
      readDirectory:()=>[...this.files.values()].map(e=>[e.path,v.FileType.File]),readFile:uri=>{const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);return Buffer.from(e.text.toString());},
      writeFile:async(uri,bytes)=>{const e=entryFor(uri);if(!e)throw v.FileSystemError.FileNotFound(uri);if(Buffer.from(bytes).toString('utf8')!==e.text.toString())throw v.FileSystemError.Unavailable('El búfer está cambiando. Vuelve a guardar.');await this.sync();await this.request({action:'save',path:e.path});},rename:denied,delete:denied,createDirectory:denied
    },{isCaseSensitive:true}));
    this.disposables.push(v.workspace.onDidChangeTextDocument(event=>{const entry=[...this.files.values()].find(e=>e.doc===event.document);if(!entry||this.applying)return;entry.crdt.transact(()=>{for(const edit of [...event.contentChanges].sort((a,b)=>b.rangeOffset-a.rangeOffset)){if(edit.rangeLength)entry.text.delete(edit.rangeOffset,edit.rangeLength);if(edit.text)entry.text.insert(edit.rangeOffset,edit.text);}},'local');}));
    await this.sync();for(const entry of this.files.values())await v.window.showTextDocument(entry.doc);this.timer=setInterval(()=>this.sync().catch(e=>this.output.appendLine(e.message)),500);
  }
  sync(){const operation=this.serial.catch(()=>{}).then(()=>this.performSync());this.serial=operation;return operation;}
  async performSync(){
    if(this.stopped)return;const sent=this.pending;this.pending=new Map();
    try{const result=await this.request({action:'sync',peer:this.peer,name:this.name,vectors:Object.fromEntries([...this.files].map(([path,e])=>[path,Buffer.from(Y.encodeStateVector(e.crdt)).toString('base64')])),updates:Object.fromEntries([...sent].map(([path,updates])=>[path,Buffer.from(Y.mergeUpdates(updates)).toString('base64')]))});
      this.allowRun=result.allowRun;
      for(const [path,update] of Object.entries(result.updates)){let entry=this.files.get(path);if(!entry){const crdt=new Y.Doc();entry={crdt,text:crdt.getText('text')};entry.undo=new Y.UndoManager(entry.text,{trackedOrigins:new Set(['local'])});this.files.set(path,entry);crdt.on('update',(update,origin)=>{if(origin==='remote')return;if(!this.pending.has(path))this.pending.set(path,[]);this.pending.get(path).push(update);});}
        Y.applyUpdate(entry.crdt,Buffer.from(update,'base64'),'remote');const text=entry.text.toString();if(!entry.doc){entry.path=path;entry.uri=v.Uri.from({scheme:'zenit-team',authority:result.room,path:'/'+path});entry.doc=await v.workspace.openTextDocument(entry.uri);await v.languages.setTextDocumentLanguage(entry.doc,this.language(path));}
        else if(entry.doc.getText()!==text){const before=entry.doc.getText();let start=0,end=0;while(start<before.length&&start<text.length&&before[start]===text[start])start++;while(end<before.length-start&&end<text.length-start&&before[before.length-1-end]===text[text.length-1-end])end++;const edit=new v.WorkspaceEdit();edit.replace(entry.doc.uri,new v.Range(entry.doc.positionAt(start),entry.doc.positionAt(before.length-end)),text.slice(start,text.length-end));this.applying=true;try{if(!await v.workspace.applyEdit(edit))throw Error('El editor rechazó una actualización.');}finally{this.applying=false;}}
      }
    }catch(error){for(const [path,updates] of sent)this.pending.set(path,[...updates,...this.pending.get(path)||[]]);throw error;}
  }
  language(path){const ext=path.split('.').at(-1);return {py:'python',c:'c',cpp:'cpp',h:'c',hpp:'cpp',java:'java',js:'javascript',ts:'typescript',nc:'nc',asm:'asm',json:'json',md:'markdown'}[ext]||'plaintext';}
  current(){const doc=v.window.activeTextEditor?.document;const entry=[...this.files.values()].find(e=>e.doc===doc);if(!entry)throw Error('Selecciona uno de los búferes compartidos.');return entry;}
  async save(){const entry=this.current();if(!await entry.doc.save())throw Error('No se pudo guardar el búfer compartido.');v.window.showInformationMessage('Guardado en el anfitrión: '+entry.path);}
  async run(){const entry=this.current();await this.sync();const {job}=await this.request({action:'run',path:entry.path});this.output.show(true);let offset=0;while(!this.stopped){const data=await this.request({action:'job',job,offset});offset=data.offset;this.output.append(data.output);if(data.done)break;await new Promise(resolve=>setTimeout(resolve,300));}}
  async undo(){this.current().undo.undo();await this.sync();}
  stop(){this.stopped=true;clearInterval(this.timer);this.request({action:'leave',peer:this.peer}).catch(()=>{});this.disposables.forEach(x=>x.dispose());for(const e of this.files.values()){e.undo.destroy();e.crdt.destroy();}this.output.dispose();}
}
exports.Client=Client;
exports.activate=context=>{
  const command=(name,fn)=>context.subscriptions.push(v.commands.registerCommand(name,async()=>{try{return await fn();}catch(e){v.window.showErrorMessage('Co-Code: '+e.message);}}));
  command('zenit.team.join',async()=>{const invite=await v.window.showInputBox({title:'Invitación de Zénit',prompt:'Solo se comparten los archivos seleccionados por el anfitrión.',password:true});if(!invite)return;const name=await v.window.showInputBox({title:'Tu nombre',value:'Programador'});if(name===undefined)return;active?.stop();active=new Client(invite,name);await active.start();});
  command('zenit.team.leave',()=>{active?.stop();active=null;});command('zenit.team.save',()=>active?.save());command('zenit.team.run',()=>active?.run());command('zenit.team.undo',()=>active?.undo());context.subscriptions.push({dispose(){active?.stop();}});
};
exports.deactivate=()=>active?.stop();
