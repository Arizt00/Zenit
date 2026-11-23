// Preview extensions run in separate killable Node processes, not a security sandbox.
const readline=require('node:readline'),Module=require('node:module'),{pathToFileURL,fileURLToPath}=require('node:url');
const createAPI=require('./extension_api.cjs'),write=process.stdout.write.bind(process.stdout);
console.log=console.info=(...args)=>process.stderr.write(args.map(String).join(' ')+'\n');
// Helpers launched by extensions must never create incidental CMD windows.
const cp=require('node:child_process');
for(const name of ['spawn','spawnSync','execFile','execFileSync']){const original=cp[name];cp[name]=function(command,args,options,...rest){if(!Array.isArray(args)){rest=[options,...rest];options=args;args=[];}if(typeof options==='function'){rest.unshift(options);options={};}return original.call(this,command,args,{...options,windowsHide:true},...rest.filter(x=>x!==undefined));};}
const commands=new Map(),providers=[],tokens=[],actions=new Map(),completions=new Map();let actionSequence=0,completionSequence=0;let active={path:'',text:'',language:'plaintext'},effects=[],bridge,loaded=false;
const pendingServices=new Map();let serviceSequence=0;
function service(method,params={}){const id=++serviceSequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pendingServices.delete(id);reject(Error('El servicio '+method+' no respondió.'));},45000);pendingServices.set(id,{resolve,reject,timer});write(JSON.stringify({type:'service',id,method,params})+'\n');});}
const disposable=fn=>({dispose:fn||(()=>{})});
const cancellation=require('./extension_cancellation.cjs'),providerRequests=new Map();
let capabilityTimer;
function capabilitiesChanged(){if(!loaded)return;clearTimeout(capabilityTimer);capabilityTimer=setTimeout(()=>service('runtime.capabilities',capabilities()).catch(e=>console.error(e.message)),30);}
const registerCommand=(id,fn,title=id)=>{commands.set(id,{fn,title});capabilitiesChanged();return disposable(()=>{commands.delete(id);capabilitiesChanged();});};
const register=(kind,language,fn,extra={})=>{const p={kind,language,fn,...extra};providers.push(p);capabilitiesChanged();return disposable(()=>{const i=providers.indexOf(p);if(i>=0)providers.splice(i,1);capabilitiesChanged();});};
const api={registerCommand,registerCompletionProvider:(l,f)=>register('completion',l,f),registerDefinitionProvider:(l,f)=>register('definition',l,f),registerInlayHintsProvider:(l,f)=>register('inlay',l,f),registerDiagnosticsProvider:(l,f)=>register('diagnostics',l,f),registerTokens:(language,rules)=>tokens.push({language,rules}),getDocument:()=>({...active}),notify:message=>effects.push({message:String(message)})};
const extensionStates=new Map(),bridges=new Map(),path=require('node:path');
function capabilities(){
 const values=providers.map(({kind,language,legend,triggers})=>({kind,language,legend,triggers}));
 for(const b of bridges.values())if(b.diagnosticCollections.size)for(const language of b.context.extension?.packageJSON?.contributes?.languages||[])values.push({kind:'diagnostics',language:language.id});
 return {commands:[...commands].map(([id,c])=>({id,title:c.title})),providers:values,tokens,views:[...bridges.values()].flatMap(b=>b.treeViews.snapshot()),fileDecorations:[...bridges.values()].some(b=>b.hasFileDecorations()),terminalLinks:[...bridges.values()].some(b=>b.terminalLinks.count),tasks:[...bridges.values()].flatMap(b=>b.services.taskTypes()),notebooks:[...bridges.values()].some(b=>!!b.context.extension?.packageJSON?.contributes?.notebookRenderer),unsupportedApis:[...new Set([...bridges.values()].flatMap(b=>[...b.unsupportedApis]))],providerErrors:providers.filter(p=>p.lastFailure).slice(0,16).map(p=>({kind:p.kind,language:p.language,message:p.lastFailure}))};
}
const {AsyncLocalStorage}=require('node:async_hooks'),extensionScope=new AsyncLocalStorage();
function owner(parent){const file=parent?.filename?.toLowerCase();if(file)for(const [root,b] of bridges)if(file.startsWith(root+path.sep))return b;return extensionScope.getStore()||bridge;}
const original=Module._load;Module._load=function(id,parent,...args){return id==='vscode'?owner(parent).vscode:id==='lumen'?api:original.call(this,id,parent,...args);};
// ESM imports do not pass through Module._load. Resolve them to the *same*
// per-extension API object; keep named/default imports and CJS identity intact.
// Synchronous hooks run on this thread, preserving callbacks and scoped state.
const esmAPIs=new Map();globalThis[Symbol.for('zenit.extension.esm')]=esmAPIs;
if(Module.registerHooks)Module.registerHooks({
  resolve(specifier,context,nextResolve){
    if(specifier!=='vscode')return nextResolve(specifier,context);
    let b;if(context.parentURL?.startsWith('file:'))b=owner({filename:fileURLToPath(context.parentURL)});
    if(!b)throw Error('Import vscode fuera de una extensión autorizada.');
    const key=b.context.extensionPath;esmAPIs.set(key,b.vscode);
    return {url:'zenit-vscode:'+encodeURIComponent(key),format:'module',shortCircuit:true};
  },
  load(url,context,nextLoad){
    if(!url.startsWith('zenit-vscode:'))return nextLoad(url,context);
    const key=decodeURIComponent(url.slice('zenit-vscode:'.length)),vscode=esmAPIs.get(key);
    if(!vscode)throw Error('La API de la extensión ya no está disponible.');
    const names=Object.keys(vscode).filter(name=>/^[A-Za-z_$][\w$]*$/.test(name)&&name!=='default');
    const source='const api=globalThis[Symbol.for("zenit.extension.esm")].get('+JSON.stringify(key)+');\nexport default api;\n'+names.map(name=>'export const '+name+'=api['+JSON.stringify(name)+'];').join('\n');
    return {source,format:'module',shortCircuit:true};
  }
});
async function request(message,token=cancellation.none){
  if(token.isCancellationRequested)return {items:[],cancelled:true};
  if(message.method==='activateFromFile'){
    if(loaded||message.bytes<1||message.bytes>20000000)throw Error('Metadatos de activación inválidos.');
    const fs=require('node:fs'),crypto=require('node:crypto'),file=fs.openSync(message.file,'r');let raw;
    try{const info=fs.fstatSync(file);if(!info.isFile()||info.size!==message.bytes)throw Error('Tamaño de activación inválido.');raw=fs.readFileSync(file);}finally{fs.closeSync(file);}
    if(crypto.createHash('sha256').update(raw).digest('hex')!==message.sha256)throw Error('Los metadatos de activación cambiaron.');
    const value=JSON.parse(raw);if(value.method!=='activate')throw Error('Operación de activación inválida.');return request(value);
  }
  if(message.method==='activate'){
    const authorised=[...(message.dependencies||[]),{id:message.extensionId,root:message.root,manifest:message.manifest,entry:message.entry}];
    const activateExtension=async id=>{
      const key=id.toLowerCase(),record=extensionStates.get(key);
      if(record?.active)return record.exports;
      const item=authorised.find(x=>x.id.toLowerCase()===key);if(!item)throw Error('Dependencia no autorizada: '+id);
      if(record?.activating)throw Error('Activación circular: '+id);
      extensionStates.set(key,{activating:true});
      const b=createAPI({...api,register,service,extensionState:id=>extensionStates.get(id.toLowerCase()),activateExtension,effect:e=>effects.push(e),commandIds:()=>[...commands.keys()],execute:async(id,args)=>{if(commands.has(id))return commands.get(id).fn(...args);if(id==='setContext')return service('context.set',{key:args[0],value:args[1]});if(id==='vscode.open')return b.vscode.window.showTextDocument(args[0],args[1]);if(id==='vscode.openWith')return b.services.openWith(...args);if(id==='workbench.action.tasks.runTask')return b.services.runTask(args[0]);return service('command.execute',{id,args});}},{...message,id:item.id,root:item.root,manifest:item.manifest,storage:path.join(path.dirname(message.storage),item.id)});
      bridges.set(path.resolve(item.root).toLowerCase(),b);if(key===message.extensionId.toLowerCase())bridge=b;
      const declared=item.manifest.lumen?.main||item.manifest.main;
      let entry=item.entry||path.resolve(item.root,declared||'');
      if(declared&&!require('node:fs').existsSync(entry)&&require('node:fs').existsSync(entry+'.js'))entry+='.js';
      if(declared||item.entry){
        const relative=path.relative(item.root,entry);if(relative.startsWith('..')||path.isAbsolute(relative))throw Error('main fuera de la extensión: '+item.id);
        const value=await extensionScope.run(b,async()=>{const extension=await import(pathToFileURL(entry).href),target=extension.default||extension;if(typeof target.activate!=='function')throw Error('La extensión no exporta activate(): '+item.id);return target.activate(b.context,api);});
        extensionStates.set(key,{active:true,exports:value});
      }else extensionStates.set(key,{active:true,exports:undefined});
      for(const command of item.manifest.contributes?.commands||[])if(commands.has(command.command))commands.get(command.command).title=command.title;
      return extensionStates.get(key).exports;
    };
    for(const item of authorised)await activateExtension(item.id);loaded=true;
    const manifest=message.manifest;
    for(const command of manifest.contributes?.commands||[])if(commands.has(command.command))commands.get(command.command).title=command.title;
    return {...capabilities(),dependencies:authorised.slice(0,-1).map(x=>x.id)};
  }
  // Panels can acknowledge their startup while activate()/a command is still
  // awaiting that acknowledgement. Only this UI channel is reentrant; editor
  // requests remain serialized to preserve each document snapshot.
  if(message.method==='webviewMessage'){for(const b of bridges.values()){const result=await b.services.message(message.panel,message.message);if(result.delivered)return result;}return {delivered:false};}
  if(message.method==='webviewDispose'){for(const b of bridges.values())b.services.disposePanel(message.panel);return {ok:true};}
  if(!loaded)throw Error('Extensión no activada.');
  if(message.method==='debugVisualization')return bridge.services.visualize(message.visualization);
  if(message.method==='ports'){const items=[];for(const b of bridges.values())items.push(...(await b.portAttributes(message.ports)).items);return {items};}
  effects=[];
  if(message.document){
    for(const document of message.documents||[])for(const b of bridges.values())b.syncDocument(document);
    active=message.document;for(const b of bridges.values())b.syncDocument(active);
  }
  if(message.method==='notebook')return bridge.notebooks.control(message);
  if(message.method==='tasks'){
    if(message.action==='list'){const tasks=[];for(const b of bridges.values())tasks.push(...await b.services.listTasks());return {tasks};}
    for(const b of bridges.values()){if(message.name&&!((await b.services.listTasks()).some(t=>t.name===message.name)))continue;const execution=await b.services.runTask(message.name);if(execution)return {result:{id:execution._id,name:execution.task.name},effects};}
    return {result:null,effects};
  }
  if(message.method==='willSave'){const edits=[];for(const b of bridges.values())edits.push(...(await b.willSave(message.reason)).edits);return {edits};}
  if(message.method==='didSave'){for(const b of bridges.values())b.didSave();return {ok:true};}
  if(message.method==='virtual'){for(const b of bridges.values())if(b.hasVirtual(message.uri))return {text:await b.readVirtual(message.uri)};throw Error('Documento virtual no registrado.');}
  if(message.method==='decorations'){if(bridges.size===1)return bridge.fileDecorations(message.paths,message.revision);const items=[];let revision=0;for(const b of bridges.values()){const r=await b.fileDecorations(message.paths);items.push(...r.items||[]);revision+=r.revision||0;}return {items,revision};}
  if(message.method==='terminalLinks'){const items=[];for(const b of bridges.values())items.push(...(await b.terminalLinks.provide(message)).items);return {items};}
  if(message.method==='terminalLink'){for(const b of bridges.values())if(b.terminalLinks.has(message.link)){await b.terminalLinks.activate(message.link);break;}return {effects};}
  if(message.method==='editSessionIdentity')return bridge.editSessionIdentity(message);
  if(message.method==='treeCheckbox'){const b=[...bridges.values()].find(x=>x.treeViews.snapshot().some(v=>v.id===message.view));return b.treeViews.checkbox(message.view,message.element,message.checkboxState);}
  if(message.method==='tree'){const b=[...bridges.values()].find(x=>x.treeViews.snapshot().some(v=>v.id===message.view));if(message.view&&!b)throw Error('Vista de extensión no registrada: '+message.view);return message.view?b.treeViews.children(message.view,message.element):{views:[...bridges.values()].flatMap(x=>x.treeViews.snapshot())};}
  if(message.method==='command'){
    const c=commands.get(message.command);if(!c)throw Error('Comando no registrado.');
    const args=(message.arguments||[]).map(value=>{const ref=value?.$lumenTreeElement;if(!ref)return value;const b=[...bridges.values()].find(x=>x.treeViews.snapshot().some(v=>v.id===ref.view));if(!b)throw Error('Vista de argumento no registrada.');return b.treeViews.arguments([value])[0];});
    return {result:await c.fn(...(c.fn.vscodeCommand?[]:[{...active}]),...args),effects};
  }
  if(message.method==='resolveAction'){
    const cached=actions.get(message.action);if(!cached)throw Error('La corrección caducó. Solicita de nuevo las acciones.');
    if(cached.path!==active.path||cached.text!==active.text)throw Error('El archivo cambió. Solicita de nuevo las acciones.');
    return {action:cached.provider.resolver?await cached.provider.resolver(cached.item,token)||cached.item:cached.item};
  }
  if(message.method==='provide'){
    const result=[],providerErrors=[],snapshot={...active};let incomplete=false;
    for(const p of providers.filter(p=>p.kind===message.kind&&(p.language===active.language||p.language==='*'))){
      let value,items;
      if(token.isCancellationRequested)return {items:[],cancelled:true};
      try{value=await p.fn({...snapshot,token,position:message.position,range:message.range,newName:message.newName,context:message.context,options:message.options,character:message.character,positions:message.positions,color:message.color});if(token.isCancellationRequested)return {items:[],cancelled:true};items=Array.isArray(value)?value:(value?.items||value?.hints||(value?[value]:[]));if(!Array.isArray(items))throw Error('El proveedor devolvió una lista no válida.');if(p.lastFailure){delete p.lastFailure;capabilitiesChanged();}}
      catch(error){if(token.isCancellationRequested)return {items:[],cancelled:true};const text=String(error?.message||error).slice(0,500);if(p.lastFailure!==text){console.error('Proveedor '+p.kind+' ('+p.language+'): '+text);p.lastFailure=text;capabilitiesChanged();}if(providerErrors.length<16)providerErrors.push({kind:p.kind,message:text});continue;}
      if(message.kind==='completion'&&value?.isIncomplete)incomplete=true;
      if(message.kind==='actions')for(const item of items){const key=String(++actionSequence);actions.set(key,{provider:p,item,path:snapshot.path,text:snapshot.text});if(actions.size>256)actions.delete(actions.keys().next().value);result.push({...item,_lumenAction:key});}
      else if(message.kind==='completion')for(const item of items){
        if(!p.resolver){result.push(item);continue;}
        const key=String(++completionSequence);completions.set(key,{provider:p,item,path:snapshot.path,text:snapshot.text});if(completions.size>512)completions.delete(completions.keys().next().value);result.push({...item,_lumenCompletion:key});
      }
      else result.push(...items);
    }
    if(message.kind==='diagnostics')for(const b of bridges.values())result.push(...b.getDiagnostics().map(d=>({line:d.range.start.line+1,column:d.range.start.character+1,endLine:d.range.end.line+1,endColumn:d.range.end.character+1,message:d.message,severity:['error','warning','info','hint'][d.severity||0]})));
    return {items:result,...(message.kind==='completion'?{incomplete}:{}),...(providerErrors.length?{providerErrors}:{})};
  }
  if(message.method==='resolveCompletion'){
    const cached=completions.get(message.completion);if(!cached)throw Error('La sugerencia caducó. Solicita de nuevo las sugerencias.');
    if(cached.path!==active.path||cached.text!==active.text)throw Error('El archivo cambió. Solicita de nuevo las sugerencias.');
    if(!cached.resolved){cached.item=await cached.provider.resolver(cached.item,token)||cached.item;if(!token.isCancellationRequested)cached.resolved=true;}
    return {item:cached.item};
  }
  throw Error('Método no disponible en la API preview.');
}
let queue=Promise.resolve();
readline.createInterface({input:process.stdin}).on('line',line=>{
  let message;try{message=JSON.parse(line);}catch{return;}
  if(message.type==='cancelRequest'){providerRequests.get(message.id)?.cancel();return;}
  if(message.type==='serviceResult'){const p=pendingServices.get(message.id);if(p){pendingServices.delete(message.id);clearTimeout(p.timer);message.error?p.reject(Error(message.error)):p.resolve(message.result);}return;}
  if(message.type==='serviceEvent'){if(message.name==='editor.state'){const editor=message.value.editors?.find(e=>e.active)||message.value.editors?.[0];if(editor)active={path:editor.path,text:editor.text,language:editor.language,dirty:editor.dirty};}for(const b of bridges.values()){b.uiEvent?.(message.name,message.value);b.services?.event(message.name,message.value);}return;}
  if(message.method==='webviewMessage'||message.method==='webviewDispose'){
    request(message).then(result=>write(JSON.stringify({id:message.id,result})+'\n'),error=>write(JSON.stringify({id:message.id,error:error.message})+'\n'));return;
  }
  const source=['provide','resolveAction','resolveCompletion'].includes(message.method)?cancellation.source():null;
  if(source)providerRequests.set(message.id,source);
  queue=queue.then(async()=>{try{let result=await request(message,source?.token);if(source?.token.isCancellationRequested)result={items:[],cancelled:true};const text=JSON.stringify({id:message.id,result},(_,v)=>v instanceof Uint32Array?[...v]:v);if(Buffer.byteLength(text)>2000000)throw Error('Respuesta de extensión demasiado grande.');write(text+'\n');}catch(error){if(source?.token.isCancellationRequested)write(JSON.stringify({id:message.id,result:{items:[],cancelled:true}})+'\n');else{console.error(error.stack||error.message);write(JSON.stringify({id:message.id,error:error.message})+'\n');}}finally{providerRequests.delete(message.id);source?.dispose();}});
});
