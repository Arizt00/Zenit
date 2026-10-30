import * as Y from '/team-vendor/yjs.mjs';
import {SharedExecutions} from '/team-execution.js';
import {CoCoDrafts} from '/coco-drafts.js';
import {CoCoRunIntents} from '/coco-intents.js';
const $=s=>document.querySelector(s),key=location.hash.slice(1),identityKey='coco:'+key,files=new Map();
let identity;try{identity=JSON.parse(sessionStorage.getItem(identityKey));}catch{}identity||={peer:crypto.randomUUID()};
// Persist before the first sync: its acknowledgement can be lost in transit.
identity.resumeKey||=Array.from(crypto.getRandomValues(new Uint8Array(32)),x=>x.toString(16).padStart(2,'0')).join('');
try{sessionStorage.setItem(identityKey,JSON.stringify(identity));}catch{}
let current,editor,busy=false,running=false,applying=false,timer,syncError=false,pending=new Map(),tree=[],treeVersion,permissions={edit:true},snapshot,drafts;
const executions=new SharedExecutions(request),runIntents=new CoCoRunIntents();
const encode=bytes=>{let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);},decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function request(body){
  for(let attempt=0;attempt<2;attempt++){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);let response,result;
    try{response=await fetch('/v1',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({...body,...identity}),signal:controller.signal});result=await response.json();}
    catch(error){if(attempt||!(body.action==='run'&&body.requestId||body.action==='sync'&&identity.resumeKey||['project-create','project-rename'].includes(body.action)&&body.operationId))throw error;continue;}finally{clearTimeout(timeout);}
    if(!response.ok)throw Error(result.error||'Conexión rechazada.');return result;
  }
}
function status(text){$('#status').textContent=text;}
function language(path){return {py:'python',cpp:'cpp',c:'c',nc:'nc',asm:'asm',java:'java',js:'javascript',ts:'typescript',json:'json',toml:'toml',rs:'rust'}[path.split('.').at(-1)]||'plaintext';}
function choose(path){if(!files.has(path))return;current=path;editor.setModel(files.get(path).model);editor.updateOptions({readOnly:!permissions.edit});for(const b of $('#files').children)b.setAttribute('aria-pressed',String(b.dataset.path===path));}
function requeue(sent){for(const [path,updates] of sent)pending.set(path,[...updates,...pending.get(path)||[]]);}
function reconcile(documents){
  for(const {id,path} of documents||[]){const entry=[...files.values()].find(e=>e.id===id);if(!entry||entry.path===path)continue;const old=entry.path;files.delete(old);entry.path=path;files.set(path,entry);if(pending.has(old)){pending.set(path,[...pending.get(old),...pending.get(path)||[]]);pending.delete(old);}entry.button.textContent=path;entry.button.dataset.path=path;monaco.editor.setModelLanguage(entry.model,language(path));if(current===old)current=path;}
}
function paintProject(){
  const shared=!!snapshot?.project?.shared;$('#project-tools').hidden=!shared;document.body.classList.toggle('project-shared',shared);$('#new-file').disabled=!permissions.tree;$('#rename-file').disabled=!permissions.tree||!current;
  const query=$('#project-search').value.toLowerCase(),list=$('#project-tree');list.replaceChildren();
  const matches=tree.filter(f=>f.path.toLowerCase().includes(query));for(const file of matches.slice(0,150)){const b=document.createElement('button');b.textContent=file.path;b.disabled=!file.text;b.title=file.text?'Abrir archivo compartido':'Archivo binario · inspección local';b.onclick=()=>act(async()=>{await request({action:'project-open',path:file.path});await synchronize();choose(file.path);});list.append(b);}
  if(matches.length>150){const count=document.createElement('p');count.textContent=`${matches.length} archivos · precisa la búsqueda para ver más.`;list.append(count);}
}
async function sync(){
  clearTimeout(timer);if(busy||!running)return;busy=true;const sent=permissions.edit?pending:new Map();if(sent===pending)pending=new Map();
  try{
    const result=await request({action:'sync',name:$('#name').value,station:'Navegador · CoCo',path:current,cursor:editor.getPosition(),treeVersion,documentIds:Object.fromEntries([...files].map(([path,e])=>[path,e.id])),vectors:Object.fromEntries([...files].map(([path,e])=>[path,encode(Y.encodeStateVector(e.doc))])),updates:Object.fromEntries([...sent].map(([path,updates])=>[path,encode(Y.mergeUpdates(updates))]))});
    if(result.self?.resumeKey){identity.resumeKey=result.self.resumeKey;try{sessionStorage.setItem(identityKey,JSON.stringify(identity));}catch{}}
    runIntents.configure(result.room);snapshot=result;permissions=result.self?.permissions||{edit:true,save:result.allowRun,run:result.allowRun};if(result.acceptedUpdates===false)requeue(sent);drafts||=new CoCoDrafts(Y,result.room);reconcile(result.documents);if(result.project?.files)tree=result.project.files;treeVersion=result.project?.version;
    for(const [path,value] of Object.entries(result.updates)){
      let entry=files.get(path),fresh=false;if(!entry){fresh=true;const doc=new Y.Doc();entry={id:result.documents?.find(d=>d.path===path)?.id||path,path,doc,text:doc.getText('text')};entry.undo=new Y.UndoManager(entry.text,{trackedOrigins:new Set(['local'])});files.set(path,entry);doc.on('update',(u,origin)=>{if(origin==='remote')return;const path=entry.path;if(!pending.has(path))pending.set(path,[]);pending.get(path).push(u);drafts.schedule(entry.id,doc);clearTimeout(timer);timer=setTimeout(sync,60);});}
      Y.applyUpdate(entry.doc,decode(value),'remote');if(fresh)await drafts.restore(entry.id,entry.doc);const text=entry.text.toString();
      if(!entry.model){entry.model=monaco.editor.createModel(text,language(path));entry.model.onDidChangeContent(event=>{if(applying)return;entry.doc.transact(()=>{for(const edit of [...event.changes].sort((a,b)=>b.rangeOffset-a.rangeOffset)){if(edit.rangeLength)entry.text.delete(edit.rangeOffset,edit.rangeLength);if(edit.text)entry.text.insert(edit.rangeOffset,edit.text);}},'local');});const b=document.createElement('button');entry.button=b;b.textContent=path;b.dataset.path=path;b.onclick=()=>choose(entry.path);$('#files').append(b);}
      else if(entry.model.getValue()!==text){const before=entry.model.getValue();let start=0,end=0;while(start<before.length&&start<text.length&&before[start]===text[start])start++;while(end<before.length-start&&end<text.length-start&&before.at(-1-end)===text.at(-1-end))end++;const a=entry.model.getPositionAt(start),b=entry.model.getPositionAt(before.length-end);applying=true;try{entry.model.applyEdits([{range:new monaco.Range(a.lineNumber,a.column,b.lineNumber,b.column),text:text.slice(start,text.length-end)}]);}finally{applying=false;}}
    }
    if(!current&&files.size)choose(files.keys().next().value);editor.updateOptions({readOnly:!permissions.edit});paintProject();
    const execution=await executions.read(current,result.executions?.[current]);$('#output').textContent=execution?.text||'';syncError=false;
    $('#environment').textContent=result.environment.workspace+' · '+result.environment.host+' · '+result.environment.runtime;$('#peers').replaceChildren();for(const person of result.participants?.length?result.participants:result.peers){const node=document.createElement('div');node.textContent=person.name+(person.role?' · '+({host:'Anfitrión',viewer:'Lectura',editor:'Edición',runner:'Edición y ejecución'}[person.role]||person.role):'')+(person.path?' · '+person.path:'');$('#peers').append(node);}$('#run').disabled=!permissions.run;$('#save').disabled=!permissions.save;$('#undo').disabled=!permissions.edit;status(pending.size?'Conectado · cambios locales pendientes de confirmar':permissions.edit?'Conectado · cambios sincronizados':'Conectado · lectura. El anfitrión puede concederte edición.');
  }catch(error){syncError=true;requeue(sent);status('Reconectando. Se conservan tus cambios. '+error.message);}
  finally{busy=false;timer=setTimeout(sync,pending.size&&permissions.edit?60:document.hidden?1800:500);}
}
async function synchronize(){while(busy)await new Promise(r=>setTimeout(r,20));await sync();if(syncError)throw Error('No se ha confirmado la conexión.');}
async function act(fn){try{await fn();}catch(e){status(e.message);}}
$('#connect').onclick=()=>act(async()=>{if(key.length<32)throw Error('Necesitas la invitación completa, incluido el fragmento después de #.');if(!editor){window.require.config({paths:{vs:'/vendor/monaco/vs'}});await new Promise((resolve,reject)=>window.require(['vs/editor/editor.main'],resolve,reject));editor=monaco.editor.create($('#editor'),{automaticLayout:true,theme:matchMedia('(prefers-color-scheme:dark)').matches?'vs-dark':'vs',fontSize:14,minimap:{enabled:false},padding:{top:20},smoothScrolling:true});editor.addCommand(monaco.KeyMod.CtrlCmd|monaco.KeyCode.KeyZ,()=>{if(permissions.edit)files.get(current)?.undo.undo();});}running=true;await synchronize();$('#connect').disabled=true;});
async function flush(){await synchronize();if(pending.size)throw Error('Aún quedan cambios sin confirmar.');}
$('#save').onclick=()=>act(async()=>{await flush();await request({action:'save',path:current});status('Guardado en el anfitrión.');});
$('#run').onclick=async()=>{
  const path=current,intentKey=files.get(path)?.id||path;let intent=runIntents.get(intentKey);if(intent?.promise)return intent.promise;
  if(!intent){intent={requestId:identity.peer+':'+crypto.randomUUID()};runIntents.set(intentKey,intent);}let acknowledged=false;
  intent.promise=act(async()=>{await flush();const result=await request({action:'run',path,requestId:intent.requestId});acknowledged=true;while(running){const data=await executions.read(path,result);if(!data)break;if(current===path)$('#output').textContent=data.text;if(data.done)break;await new Promise(r=>setTimeout(r,300));}});
  try{await intent.promise;}finally{intent.promise=null;if(acknowledged)runIntents.delete(intentKey);}
};
$('#undo').onclick=()=>{if(permissions.edit)files.get(current)?.undo.undo();};$('#project-search').oninput=paintProject;
$('#new-file').onclick=()=>act(async()=>{const path=prompt('Ruta del nuevo archivo dentro del proyecto');if(!path)return;await mutation({action:'project-create',path});await synchronize();choose(path);});
$('#rename-file').onclick=()=>act(async()=>{const newPath=prompt('Nueva ruta del archivo',current);if(!newPath||newPath===current)return;await mutation({action:'project-rename',path:current,newPath});await synchronize();choose(newPath);});
window.addEventListener('pagehide',()=>{drafts?.flushAll();running=false;clearTimeout(timer);});

async function mutation(body){const intentKey=JSON.stringify([body.action,body.path,body.newPath]);let intent=runIntents.get(intentKey);if(!intent){intent={requestId:crypto.randomUUID()};runIntents.set(intentKey,intent);}const result=await request({...body,operationId:intent.requestId});runIntents.delete(intentKey);return result;}
