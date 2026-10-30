// Notebook documents retain real cells, output bytes and serializer state.
const fs=require('node:fs'),path=require('node:path');
module.exports=function(v,host,event,makeDocument,documents){
 const books=new Map(),serializers=new Map(),controllers=new Map(),editors=new Map();let active;
 const token={isCancellationRequested:false,onCancellationRequested:event('notebookCancellation').event};
 v.NotebookCellKind={Markup:1,Code:2};v.NotebookCellExecutionState={Idle:1,Pending:2,Executing:3};
 v.NotebookRange=class{constructor(start,end){this.start=Math.max(0,Math.min(start,end));this.end=Math.max(start,end);}get isEmpty(){return this.start===this.end;}with(value){return new v.NotebookRange(value.start??this.start,value.end??this.end);}};
 v.NotebookCellData=class{constructor(kind,value,languageId){Object.assign(this,{kind,value,languageId,outputs:[],metadata:{}});}};
 v.NotebookData=class{constructor(cells){Object.assign(this,{cells,metadata:{}});}};
 v.NotebookCellOutputItem=class{
  constructor(data,mime){Object.assign(this,{data:Uint8Array.from(data),mime});}
  static text(value,mime='text/plain'){return new this(Buffer.from(value),mime);}
  static json(value,mime='text/x-json'){return this.text(JSON.stringify(value),mime);}
  static stdout(value){return this.text(value,'application/vnd.code.notebook.stdout');}
  static stderr(value){return this.text(value,'application/vnd.code.notebook.stderr');}
  static error(value){return this.json({name:value.name,message:value.message,stack:value.stack},'application/vnd.code.notebook.error');}
 };
 v.NotebookCellOutput=class{constructor(items,metadata={}){Object.assign(this,{items,metadata,id:require('node:crypto').randomUUID()});}};
 v.NotebookCellStatusBarAlignment={Left:1,Right:2};v.NotebookCellStatusBarItem=class{constructor(text,alignment){Object.assign(this,{text,alignment});}};
 const publish=book=>{const state={uri:book.uri.toString(),reveal:book._reveal||0,type:book.notebookType,dirty:book.isDirty,controllers:[...controllers.values()].filter(c=>c.notebookType===book.notebookType).map(c=>({id:c.id,label:c.label,description:c.description})),cells:book.getCells().map(c=>({kind:c.kind,language:c.document.languageId,text:c.document.getText(),outputs:c.outputs.map(o=>({items:o.items.map(i=>({mime:i.mime,data:Buffer.from(i.data).toString('base64')}))})),executionSummary:c.executionSummary})),selected:book._controller};state.version=++book._publishVersion;state.source=builtin.serializeNotebook(data(book)).toString('utf8');state.before=book._publishedSource||book._initialSource;if(book.isDirty||book._publishedSource)book._publishedSource=state.source;return host.service('notebook.update',state).catch(e=>console.error(e.message));};
 const data=book=>({_raw:book._raw,metadata:book.metadata,cells:book.getCells().map(c=>Object.assign(new v.NotebookCellData(c.kind,c.document.getText(),c.document.languageId),{_raw:c._raw,outputs:c.outputs,metadata:c.metadata,executionSummary:c.executionSummary}))});
 function cell(book,row,index){
  const uri=v.Uri.from({scheme:'vscode-notebook-cell',path:book.uri.path,fragment:String(index)}),doc=makeDocument({uri,text:row.value,language:row.languageId});documents.set(uri.toString(),doc);
  return {index,notebook:book,kind:row.kind,document:doc,metadata:row.metadata||{},outputs:row.outputs||[],executionSummary:row.executionSummary,_raw:row._raw};
 }
 const builtin=require('./extension_ipynb.cjs')(v);
 async function open(value,content){
  const uri=typeof value==='string'?v.Uri.from({scheme:'untitled',path:'/Untitled-'+(books.size+1)+'.ipynb'}):value,type=typeof value==='string'?value:'jupyter-notebook',key=uri.toString();
  if(books.has(key))return books.get(key);
  const serializer=serializers.get(type)||builtin,bytes=content?null:await fs.promises.readFile(uri.fsPath),raw=content||await serializer.deserializeNotebook(bytes,token),digest=b=>require('node:crypto').createHash('sha256').update(b).digest('hex');let revision=bytes?digest(bytes):null;
  const book={uri,notebookType:type,version:1,isDirty:uri.scheme==='untitled',isClosed:false,isUntitled:uri.scheme==='untitled',metadata:raw.metadata||{},_raw:raw._raw,_publishVersion:0,_initialSource:bytes?.toString('utf8'),_cells:[],get cellCount(){return this._cells.length;},cellAt(i){if(i<0||i>=this.cellCount)throw Error('Notebook cell out of range');return this._cells[i];},getCells(r){return r?this._cells.slice(r.start,r.end):[...this._cells];},async save(){if(uri.scheme!=='file')return false;if(digest(await fs.promises.readFile(uri.fsPath))!==revision)throw Error('El cuaderno cambió en disco. Vuelve a abrirlo antes de guardar.');const bytes=await serializer.serializeNotebook(data(this),token);const temporary=uri.fsPath+'.'+require('node:crypto').randomUUID()+'.tmp';try{await fs.promises.writeFile(temporary,bytes);await fs.promises.rename(temporary,uri.fsPath);}finally{await fs.promises.rm(temporary,{force:true});}revision=digest(bytes);this.isDirty=false;event('notebookSave').fire(this);publish(this);return true;}};
  book._cells=raw.cells.map((row,i)=>cell(book,row,i));books.set(key,book);event('notebookOpen').fire(book);return book;
 }
 Object.defineProperty(v.workspace,'notebookDocuments',{get:()=>[...books.values()]});
 Object.assign(v.workspace,{openNotebookDocument:open,registerNotebookSerializer:(type,serializer)=>{serializers.set(type,serializer);return new v.Disposable(()=>serializers.delete(type));},onDidOpenNotebookDocument:event('notebookOpen').event,onDidCloseNotebookDocument:event('notebookClose').event,onDidChangeNotebookDocument:event('notebookChange').event,onDidSaveNotebookDocument:event('notebookSave').event});
 Object.defineProperties(v.window,{activeNotebookEditor:{get:()=>active},visibleNotebookEditors:{get:()=>[...editors.values()]}});
 Object.assign(v.window,{onDidChangeActiveNotebookEditor:event('activeNotebook').event,onDidChangeVisibleNotebookEditors:event('visibleNotebooks').event,onDidChangeNotebookEditorSelection:event('notebookSelection').event,onDidChangeNotebookEditorVisibleRanges:event('notebookVisibleRanges').event,async showNotebookDocument(value){const book=value?.getCells?value:await open(value);let editor=editors.get(book.uri.toString());if(!editor){editor={notebook:book,selection:new v.NotebookRange(0,Math.min(1,book.cellCount)),selections:[],visibleRanges:[new v.NotebookRange(0,book.cellCount)],viewColumn:1,revealRange(){}};editors.set(book.uri.toString(),editor);}book._reveal=(book._reveal||0)+1;active=editor;event('activeNotebook').fire(editor);event('visibleNotebooks').fire([...editors.values()]);publish(book);return editor;}});
 v.notebooks={onDidChangeNotebookCellExecutionState:event('cellExecution').event,createNotebookController(id,notebookType,label,handler){
  if(controllers.has(id))throw Error('Duplicate notebook controller');const c={id,notebookType,label,executeHandler:handler,supportedLanguages:[],supportsExecutionOrder:false,onDidChangeSelectedNotebooks:event('controllerSelected:'+id).event,updateNotebookAffinity(){},dispose(){controllers.delete(id);for(const b of books.values())publish(b);},createNotebookCellExecution(cell){
   const book=cell.notebook;if(book._controller!==id)throw Error('Select this notebook controller before executing.');let ended=false;
   const change=()=>{book.version++;book.isDirty=true;event('notebookChange').fire({notebook:book,cellChanges:[{cell,outputs:cell.outputs,executionSummary:cell.executionSummary}],contentChanges:[],metadata:undefined});publish(book);};
   const execution={cell,token,executionOrder:undefined,start(time){cell.executionSummary={timing:{startTime:time||Date.now()},executionOrder:this.executionOrder};event('cellExecution').fire({cell,state:3});change();},end(success,time){if(ended)return;ended=true;cell.executionSummary={...cell.executionSummary,success,executionOrder:this.executionOrder,timing:{...cell.executionSummary?.timing,endTime:time||Date.now()}};event('cellExecution').fire({cell,state:1});change();},async clearOutput(target=cell){target.outputs=[];change();},async replaceOutput(values,target=cell){target.outputs=Array.isArray(values)?values:[values];change();},async appendOutput(values,target=cell){target.outputs.push(...(Array.isArray(values)?values:[values]));change();},async replaceOutputItems(items,output){output.items=items;change();},async appendOutputItems(items,output){output.items.push(...items);change();}};return execution;
  }};controllers.set(id,c);for(const book of books.values())publish(book);return c;
 }};
 return {async control(message){
  const book=await open(v.Uri.parse(message.uri));
  if(message.action==='open')return v.window.showNotebookDocument(book).then(()=>({opened:true}));
  if(message.action==='save')return {saved:await book.save()};
  if(message.action==='select'){if(!controllers.has(message.controller))throw Error('Notebook controller unavailable');book._controller=message.controller;event('controllerSelected:'+message.controller).fire({notebook:book,selected:true});publish(book);return {selected:true};}
  if(message.action==='execute'){const c=controllers.get(book._controller);if(!c?.executeHandler)throw Error('Selecciona un kernel preparado para ejecutar este cuaderno.');if(book._running)throw Error('El cuaderno ya está ejecutando celdas.');book._running=true;Promise.resolve(c.executeHandler(message.index===undefined?book.getCells().filter(c=>c.kind===2):[book.cellAt(message.index)],book,c)).catch(e=>host.notify(e.message)).finally(()=>{book._running=false;publish(book);});return {started:true};}
  if(message.action==='interrupt'){const c=controllers.get(book._controller);if(c?.interruptHandler)await c.interruptHandler(book);return {stopped:true};}
  if(message.action==='edit'){const old=book.cellAt(message.index),next=cell(book,{...old,value:message.text,languageId:old.document.languageId},old.index);book._cells[old.index]=next;book.version++;book.isDirty=true;event('notebookChange').fire({notebook:book,cellChanges:[{cell:next,document:next.document}],contentChanges:[]});publish(book);return {changed:true};}
  throw Error('Notebook operation unavailable');
 }};
};
