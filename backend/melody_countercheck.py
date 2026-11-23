"""Reviewed, cancellable A/B runs of saved code and an unsaved buffer."""
import copy,difflib,hashlib,os,shutil,tempfile,threading,time,uuid
from pathlib import Path
from concurrent.futures import CancelledError
from .lantern_adapters import stage,prepare,Superseded
from .workspace import Workspace

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

class MelodyCountercheck:
 def __init__(self,features):self.f=features;self.plans={};self.lock=threading.RLock()
 def plan(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de preparar Contraprueba.')
  destination=self.f.execution.reviewed_target(ws)
  path=body.get('path','');saved=ws.read(path);content=body.get('content');stdin=body.get('stdin','');timeout=body.get('timeout',10)
  if not isinstance(content,str) or len(content.encode())>128000:raise ValueError('Selecciona un búfer de texto de hasta 128 kB.')
  if not isinstance(stdin,str) or len(stdin.encode())>16384:raise ValueError('La entrada admite hasta 16 KiB.')
  if type(timeout) not in (int,float) or not 1<=timeout<=60:raise ValueError('El límite por variante debe estar entre 1 y 60 segundos.')
  from .runtimes import language
  if language(path,self.f.runtimes.config['languages']) in (None,'html','css'):raise ValueError('Selecciona un programa ejecutable con un adaptador configurado.')
  identity=uuid.uuid4().hex
  plan=dict(id=identity,workspace=str(ws.root),path=path,saved=saved['content'],content=content,stdin=stdin,timeout=timeout,revision=saved['revision'],created=time.time(),executionTarget=destination)
  with self.lock:
   self.plans[identity]=plan
   for old in list(self.plans)[:-16]:self.plans.pop(old,None)
  return dict(id=identity,path=path,savedSha256=digest(saved['content']),bufferSha256=digest(content),same=saved['content']==content,timeout=timeout,inputBytes=len(stdin.encode()),
   diff='\n'.join(difflib.unified_diff(saved['content'].splitlines(),content.splitlines(),fromfile='Guardado',tofile='Búfer',n=2))[:16000],
   executionTarget=destination,variants=['Guardado','Búfer'],notice='Se ejecutan dos copias revisadas en '+destination['label']+', una tras otra, con la misma entrada. Los programas mantienen los permisos de tu cuenta; las copias no son una máquina aislada.')
 def run(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de ejecutar Contraprueba.')
  destination=self.f.execution.reviewed_target(ws)
  with self.lock:
   plan=self.plans.get(body.get('plan'))
   if not plan or plan['workspace']!=str(ws.root) or time.time()-plan['created']>600:raise ValueError('La revisión ha caducado. Prepara otra Contraprueba.')
   if destination!=plan['executionTarget']:raise ValueError('El destino de ejecución cambió. Revisa de nuevo las órdenes.')
   if plan.get('task'):return plan['task']
   if ws.read(plan['path'])['revision']!=plan['revision']:raise ValueError('El archivo guardado cambió después de la revisión.')
   plan['task']=self.f.hilo.submit(getattr(self,'title','Melody · Contraprueba'),lambda event:self.execute(ws,plan,event),workspace=ws.root,key='countercheck:'+plan['id'],priority=5)
   return plan['task']
 def execute(self,ws,plan,event):
  def cancelled():return event.is_set()
  if cancelled():raise CancelledError()
  if self.f.execution.reviewed_target(ws)!=plan['executionTarget']:raise ValueError('El destino cambió mientras esperaba su turno. Prepara una nueva revisión.')
  if ws.read(plan['path'])['revision']!=plan['revision']:raise ValueError('El archivo cambió mientras esperaba su turno.')
  results=[]
  with tempfile.TemporaryDirectory(prefix='zenit-countercheck-') as folder:
   root=Path(folder)
   try:base=stage(ws,plan['path'],plan['saved'],root/'saved',cancelled)
   except Superseded:raise CancelledError()
   def copy_file(source,target):
    if cancelled():raise CancelledError()
    return shutil.copy2(source,target)
   shutil.copytree(base.root,root/'buffer',copy_function=copy_file);other=Workspace(root/'buffer',ws.native);other.trusted=True;other.python_workspace=ws
   other.resolve(plan['path']).write_text(plan['content'],encoding='utf-8',newline='')
   count=0;context=hashlib.sha256()
   for file in sorted(base.root.rglob('*')):
    if cancelled():raise CancelledError()
    if file.is_file():
     count+=1;context.update(file.relative_to(base.root).as_posix().encode());file_hash=hashlib.sha256()
     with file.open('rb') as stream:
      while chunk:=stream.read(65536):
       if cancelled():raise CancelledError()
       file_hash.update(chunk)
     context.update(file_hash.digest())
   for label,shadow,source in [('saved',base,plan['saved']),('buffer',other,plan['content'])]:
    shadow.reviewed_target=plan['executionTarget']
    if cancelled():raise CancelledError()
    self.f.hilo.report(event,'Contraprueba · '+('guardado' if label=='saved' else 'búfer'))
    try:
     runtime=prepare(self.f.runtimes,shadow,plan['path']);commands=[*runtime['checks'],*runtime['commands']]
     if not commands:raise ValueError('El adaptador no expone una ejecución por consola.')
     run=self.f.app.runner.start(commands,shadow.root,timeout=plan['timeout'],stdin=plan['stdin'],close_stdin=True,resource_class='background')
     job=self.f.app.runner.jobs[run['job']]
     while not job.done:
      if cancelled():job.cancel()
      event.wait(.04)
     if cancelled():raise CancelledError()
     results.append(dict(variant=label,sha256=digest(source),code=job.code,cancelled=job.cancelled,elapsedMs=round(job.elapsed*1000),output=job.stream_output[-16000:],log=job.output[-16000:],
      outputSha256=job.stream_sha256,outputBytes=job.stream_bytes,outputComplete=job.stream_complete and job.command_index==len(commands)-1,outputTruncated=len(job.stream_output)>16000))
    except CancelledError:raise
    except Exception as error:results.append(dict(variant=label,sha256=digest(source),code=None,error=str(error),output=''))
  a,b=results
  return dict(path=plan['path'],executionTarget=plan['executionTarget'],savedSha256=digest(plan['saved']),bufferSha256=digest(plan['content']),contextSha256=context.hexdigest(),contextFiles=count,
   inputSha256=digest(plan['stdin']),results=results,equivalent=not a.get('error') and not b.get('error') and not a.get('cancelled') and not b.get('cancelled') and a.get('outputComplete') and b.get('outputComplete') and a['code']==b['code'] and a['outputSha256']==b['outputSha256'],
   outputDiff='\n'.join(difflib.unified_diff(a['output'].splitlines(),b['output'].splitlines(),fromfile='Guardado',tofile='Búfer',n=2))[:16000])
