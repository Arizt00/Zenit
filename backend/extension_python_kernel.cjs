// A local Python session for notebook cells. It is labelled separately from
// Jupyter server kernels; no remote connection or extra dependency is implied.
const {spawn}=require('node:child_process'),readline=require('node:readline');
const script=String.raw`
import ast,contextlib,json,reprlib,sys,traceback
class Capture:
 def __init__(self):self.parts=[];self.remaining=64000
 def write(self,value):
  value=str(value)
  if self.remaining:self.parts.append(value[:self.remaining]);self.remaining=max(0,self.remaining-len(value))
  return len(value)
 def flush(self):pass
 def text(self):return ''.join(self.parts)
namespace={'__name__':'__main__'}
for line in sys.stdin:
 try:request=json.loads(line)
 except ValueError:continue
 out,err=Capture(),Capture();success=True
 try:
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   tree=ast.parse(request['code'],filename=request['file'],mode='exec')
   last=tree.body.pop() if tree.body and isinstance(tree.body[-1],ast.Expr) else None
   exec(compile(tree,request['file'],'exec'),namespace)
   if last:
    value=eval(compile(ast.Expression(last.value),request['file'],'eval'),namespace)
    if value is not None:print(reprlib.repr(value))
 except BaseException:
  success=False;err.write(traceback.format_exc())
 print(json.dumps({'id':request['id'],'success':success,'stdout':out.text(),'stderr':err.text()},ensure_ascii=False),flush=True)
`;
module.exports=function(v,options){
 const kernels=new Map();let sequence=0;
 if(!Array.isArray(options.notebookPython)||!options.notebookPython.length||!options.manifest.contributes?.notebookRenderer)return;
 const stop=book=>{const kernel=kernels.get(book.uri.toString());if(!kernel)return;kernels.delete(book.uri.toString());if(kernel.process.pid){if(process.platform==='win32')require('node:child_process').spawnSync('taskkill',['/PID',String(kernel.process.pid),'/T','/F'],{windowsHide:true,stdio:'ignore',timeout:5000});else try{process.kill(-kernel.process.pid,'SIGTERM');}catch{kernel.process.kill();}}kernel.pending?.reject(Error('Kernel reiniciado. Las variables de la sesión se han descartado.'));};
 const controller=v.notebooks.createNotebookController('zenit.local-python','jupyter-notebook','Python · Zénit (local)',async(cells,book,c)=>{
  if(kernels.get(book.uri.toString())?.pending)throw Error('El kernel ya está ejecutando una celda.');
  let kernel=kernels.get(book.uri.toString());
  if(!kernel){
   if(kernels.size>=4)throw Error('Hay cuatro kernels activos. Reinicia o cierra uno antes de abrir otro.');
   const command=options.notebookPython;let args=[...command.slice(1),'-u','-c',script];
   if(command.includes('--python-child')){const fs=require('node:fs'),path=require('node:path'),file=path.join(options.storage,'notebook-kernel.py');fs.writeFileSync(file,script);args=[...command.slice(1),file];}
   kernel={process:spawn(command[0],args,{cwd:options.workspace,windowsHide:true,detached:process.platform!=='win32',stdio:['pipe','pipe','pipe']}),order:0};kernels.set(book.uri.toString(),kernel);
   readline.createInterface({input:kernel.process.stdout}).on('line',line=>{let response;try{response=JSON.parse(line);}catch{return;}const pending=kernel.pending;if(pending&&response.id===pending.id){kernel.pending=null;pending.resolve(response);}});
   kernel.process.stderr.on('data',()=>{});
   const closed=error=>{kernels.delete(book.uri.toString());const pending=kernel.pending;kernel.pending=null;pending?.reject(error instanceof Error?error:Error('El proceso del kernel terminó.'));};kernel.process.on('error',closed);kernel.process.on('exit',closed);
  }
  for(const cell of cells){
   if(cell.kind!==v.NotebookCellKind.Code)continue;
   const execution=c.createNotebookCellExecution(cell);execution.executionOrder=++kernel.order;execution.start(Date.now());
   try{
    await execution.clearOutput();
    const result=await new Promise((resolve,reject)=>{const id=++sequence;kernel.pending={id,resolve,reject};kernel.process.stdin.write(JSON.stringify({id,code:cell.document.getText(),file:book.uri.fsPath+'#cell-'+(cell.index+1)})+'\n',e=>{if(e){kernel.pending=null;reject(e);}});});
    for(const [key,fn] of [['stdout','stdout'],['stderr','stderr']])if(result[key])await execution.appendOutput(new v.NotebookCellOutput([v.NotebookCellOutputItem[fn](result[key])]));
    execution.end(result.success,Date.now());
   }catch(error){await execution.appendOutput(new v.NotebookCellOutput([v.NotebookCellOutputItem.error(error)]));execution.end(false,Date.now());throw error;}
  }
 });
 controller.supportedLanguages=['python'];controller.supportsExecutionOrder=true;controller.interruptHandler=stop;
 v.workspace.onDidCloseNotebookDocument(stop);
 return {dispose(){for(const book of v.workspace.notebookDocuments)stop(book);controller.dispose();}};
};
