"""Explicit sequential cases on private copies, using the common runner and HILO."""
import json,shutil,tempfile
from pathlib import Path
from concurrent.futures import CancelledError
from .melody_countercheck import MelodyCountercheck,digest
from .lantern_adapters import stage,prepare,Superseded
from .workspace import Workspace
from .preferences import atomic_json

class LanternMatrix(MelodyCountercheck):
 title='Lantern · Matriz de casos'
 @staticmethod
 def normalize(body):
  cases=body.get('cases')
  if not isinstance(cases,list) or not 1<=len(cases)<=6:raise ValueError('Prepara entre uno y seis casos.')
  normalized=[]
  for i,c in enumerate(cases):
   if not isinstance(c,dict):raise ValueError('Cada caso debe ser un objeto.')
   row={'name':c.get('name',f'Caso {i+1}'),'stdin':c.get('stdin',''),'expectedOutput':c.get('expectedOutput',''),'expectedExit':c.get('expectedExit',0),'match':c.get('match','exact')}
   if any(not isinstance(row[k],str) or len(row[k].encode())>4096 for k in ('stdin','expectedOutput')) or not isinstance(row['name'],str) or len(row['name'])>80:raise ValueError('Cada caso admite 4 KiB de entrada/salida y un nombre de hasta 80 caracteres.')
   if type(row['expectedExit']) is not int or not -255<=row['expectedExit']<=255 or row['match'] not in ('exact','contains'):raise ValueError('Expectativa de caso no válida.')
   normalized.append(row)
  timeout=body.get('timeout',10)
  if type(timeout) not in (int,float) or not 1<=timeout<=60:raise ValueError('El límite por caso debe estar entre 1 y 60 segundos.')
  return {'cases':normalized,'timeout':timeout}
 def cases_file(self,ws,path):
  ws.resolve(path)
  return ws.private_dir('lantern')/digest(path)[:24]/'cases.json'
 def saved_cases(self,ws,path):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto para leer sus casos.')
  file=self.cases_file(ws,path)
  if not file.is_file():return {'path':path,'saved':False,'cases':[], 'timeout':10}
  if file.stat().st_size>60000:raise ValueError('El archivo de casos supera el límite permitido.')
  return {'path':path,'saved':True,**self.normalize(json.loads(file.read_text('utf-8')))}
 def save_cases(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto para guardar sus casos.')
  value=self.normalize(body);file=self.cases_file(ws,body.get('path',''));file.parent.mkdir(parents=True,exist_ok=True)
  atomic_json(file,value)
  return {'path':body['path'],'saved':True,**value}
 def plan(self,ws,body):
  value=self.normalize(body)
  result=super().plan(ws,{**body,'stdin':''});self.plans[result['id']]['cases']=value['cases']
  return {**result,'cases':value['cases'],'notice':'Cada caso compila y ejecuta una copia del búfer revisado en '+result['executionTarget']['label']+'. Se ejecutan de uno en uno y se cierra su entrada. Las copias mantienen los permisos de tu cuenta.'}
 def execute(self,ws,plan,event):
  if self.f.execution.reviewed_target(ws)!=plan['executionTarget']:raise ValueError('El destino cambió mientras esperaba su turno. Revisa de nuevo los casos.')
  if ws.read(plan['path'])['revision']!=plan['revision']:raise ValueError('El archivo cambió después de la revisión.')
  results=[]
  with tempfile.TemporaryDirectory(prefix='zenit-matrix-') as folder:
   root=Path(folder)
   try:base=stage(ws,plan['path'],plan['content'],root/'base',event.is_set)
   except Superseded:raise CancelledError()
   for index,case in enumerate(plan['cases']):
    if event.is_set():raise CancelledError()
    self.f.hilo.report(event,f"Caso {index+1}/{len(plan['cases'])} · {case['name']}")
    with tempfile.TemporaryDirectory(prefix='case-',dir=root) as target:
     def copy_file(source,destination):
      if event.is_set():raise CancelledError()
      return shutil.copy2(source,destination)
     shutil.copytree(base.root,target,dirs_exist_ok=True,copy_function=copy_file);shadow=Workspace(Path(target),ws.native);shadow.trusted=True;shadow.python_workspace=ws;shadow.reviewed_target=plan['executionTarget']
     try:
      runtime=prepare(self.f.runtimes,shadow,plan['path']);commands=[*runtime['checks'],*runtime['commands']]
      if not commands:raise ValueError('Este adaptador no ejecuta programas por consola.')
      run=self.f.app.runner.start(commands,shadow.root,timeout=plan['timeout'],stdin=case['stdin'],close_stdin=True,resource_class='background');job=self.f.app.runner.jobs[run['job']]
      while not job.done:
       if event.is_set():job.cancel()
       event.wait(.04)
      if event.is_set():raise CancelledError()
      output=job.stream_output.replace('\r\n','\n');expected=case['expectedOutput'].replace('\r\n','\n')
      matched=not expected or (output==expected if case['match']=='exact' else expected in output)
      passed=not job.cancelled and job.command_index==len(commands)-1 and job.code==case['expectedExit'] and job.stream_complete and matched
      results.append({'name':case['name'],'passed':passed,'code':job.code,'output':output[-8000:],'outputSha256':job.stream_sha256,'outputBytes':job.stream_bytes,'outputTruncated':len(output)>8000,'expectedOutput':expected,'expectedExit':case['expectedExit'],'elapsedMs':round(job.elapsed*1000),'log':job.output[-8000:]})
      if job.command_index!=len(commands)-1:results[-1]['error']='La preparación falló; no se alcanzó la ejecución del programa.'
     except CancelledError:raise
     except Exception as error:results.append({'name':case['name'],'passed':False,'code':None,'output':'','error':str(error)})
  return {'path':plan['path'],'executionTarget':plan['executionTarget'],'bufferSha256':digest(plan['content']),'cases':results,'passed':sum(row['passed'] for row in results),'total':len(results),'sequential':True}
