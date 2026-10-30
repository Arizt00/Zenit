"""Reviewed, bounded multi-file moves; failed/cancelled batches roll back."""
from concurrent.futures import CancelledError
import copy, hashlib, json, os, threading, time, uuid
from pathlib import Path
from .file_actions import target
from .preferences import atomic_json


class ProjectOrganizer:
 def __init__(self, features):
  self.features=features;self.lock=threading.RLock();self.plans={};self.receipts={}
  self.directory=features.prefs.directory/'explorer';self.directory.mkdir(exist_ok=True)
 def layout_file(self,ws):return self.directory/(hashlib.sha256(str(ws.root).encode()).hexdigest()[:32]+'.json')
 def layout(self,ws,body=None):
  file=self.layout_file(ws)
  with self.lock:
   if body is None:
    try:return json.loads(file.read_text('utf-8'))
    except (OSError,ValueError):return {'orders':{}}
   orders=body.get('orders',{})
   if not isinstance(orders,dict) or len(orders)>300:raise ValueError('Orden del explorador no válido.')
   clean={};total=0
   for parent,paths in orders.items():
    if not isinstance(parent,str) or not isinstance(paths,list) or len(paths)>2000:raise ValueError('Orden no válido.')
    base=ws.root if not parent else target(ws,parent,False)
    if not base.is_dir():continue
    unique=[]
    for name in paths:
     if not isinstance(name,str):raise ValueError('Ruta no válida.')
     item=target(ws,name,False)
     if item.parent!=base:raise ValueError('El orden solo puede cambiar elementos de la misma carpeta.')
     if item.exists() and name not in unique:unique.append(name)
    total+=len(unique)
    if total>10000:raise ValueError('Demasiados elementos en el orden manual.')
    if unique:clean[parent]=unique
   result={'orders':clean};atomic_json(file,result);return result
 def inventory(self,ws,paths):
  records={}
  def inspect(file):
   target(ws,file.relative_to(ws.root).as_posix())
   if file.is_symlink() or getattr(file.lstat(),'st_file_attributes',0)&0x400:raise ValueError('No se mueven enlaces ni puntos de reanálisis.')
   stat=file.stat();records[file.relative_to(ws.root).as_posix()]=[file.is_dir(),stat.st_size,stat.st_mtime_ns,stat.st_ino]
   if len(records)>10000:raise ValueError('Mueve grupos de hasta 10 000 elementos.')
  for file in paths:
   inspect(file)
   if file.is_dir():
    for folder,dirs,files in os.walk(file,followlinks=False):
     for name in dirs+files:inspect(Path(folder)/name)
  return records
 def plan(self,ws,body):
  names=body.get('paths');mode=body.get('mode','move');destination=body.get('destination','');keep=body.get('conflicts')=='keep-both'
  if not isinstance(names,list) or not 1<=len(names)<=128 or any(not isinstance(p,str) for p in names) or mode not in ('move','merge'):raise ValueError('Selecciona entre 1 y 128 archivos o carpetas.')
  roots=sorted(set(target(ws,p) for p in names),key=lambda p:(len(p.parts),str(p)))
  roots=[p for p in roots if not any(p!=q and p.is_relative_to(q) for q in roots)]
  dest=target(ws,destination) if destination else ws.root
  if not dest.is_dir():raise ValueError('El destino debe ser una carpeta.')
  if any(dest==p or dest.is_relative_to(p) for p in roots):raise ValueError('Una carpeta no puede contenerse a sí misma.')
  if mode=='merge' and any(not p.is_dir() for p in roots):raise ValueError('La fusión requiere carpetas.')
  moves=[];empty=[];conflicts=[];reserved={}
  def reserve(source,to):
   target(ws,to.relative_to(ws.root).as_posix(),False)
   if source==to:return
   if source.is_dir() and (to.is_dir() or reserved.get(to) is True):
    for child in sorted(source.iterdir()):reserve(child,to/child.name)
    empty.append(source);return
   if to.exists() or to in reserved:
    if not keep:conflicts.append(to.relative_to(ws.root).as_posix());return
    index=2;original=to
    while to.exists() or to in reserved:
     to=original.with_name(original.stem+' ('+str(index)+')'+original.suffix);index+=1
   reserved[to]=source.is_dir();moves.append((source,to))
  before=self.inventory(ws,roots)
  dest_stat=dest.stat();destination_identity=[dest_stat.st_dev,dest_stat.st_ino]
  for source in roots:
   if mode=='merge':
    for child in sorted(source.iterdir()):reserve(child,dest/child.name)
    empty.append(source)
   else:reserve(source,dest/source.name)
  # Inspect only target names at the workspace root, not unrelated project data.
  targets={str(to):to.stat().st_mtime_ns if to.exists() else None for _,to in moves}
  ident=uuid.uuid4().hex
  data={'id':ident,'workspace':str(ws.root),'created':time.time(),'mode':mode,'destination':destination,
        'moves':moves,'empty':empty,'before':before,'roots':roots,'dest':dest,'destinationIdentity':destination_identity,'targets':targets,'conflicts':sorted(set(conflicts)),'task':None}
  with self.lock:
   self.plans[ident]=data
   while len(self.plans)>24:self.plans.pop(next(iter(self.plans)))
  return {'id':ident,'mode':mode,'destination':destination,'conflicts':data['conflicts'],
          'moves':[{'from':a.relative_to(ws.root).as_posix(),'to':b.relative_to(ws.root).as_posix()} for a,b in moves],
          'folders':len(empty),'entries':len(before)}
 def apply(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de mover archivos.')
  with self.lock:
   plan=self.plans.get(body.get('plan'))
   if not plan or plan['workspace']!=str(ws.root) or time.time()-plan['created']>1800:raise ValueError('Revisa de nuevo el movimiento.')
   if plan['conflicts']:raise ValueError('Resuelve los nombres repetidos antes de mover.')
   if plan['task']:return plan['task']
   plan['task']=self.features.hilo.submit('Organizar archivos del proyecto',lambda event:self.commit(ws,plan,event),workspace=str(ws.root),key='organize:'+plan['id'],priority=-5)
   return plan['task']
 def commit(self,ws,plan,event):
  if not ws.trusted:raise PermissionError('El proyecto ya no está autorizado.')
  completed=[];created=[];removed=[]
  with ws.lock:
   if self.inventory(ws,plan['roots'])!=plan['before']:raise ValueError('Los archivos cambiaron desde la revisión. Revisa de nuevo.')
   dest_stat=plan['dest'].stat()
   if [dest_stat.st_dev,dest_stat.st_ino]!=plan['destinationIdentity']:raise ValueError('La carpeta de destino cambió desde la revisión.')
   if any((Path(p).stat().st_mtime_ns if Path(p).exists() else None)!=stamp for p,stamp in plan['targets'].items()):raise ValueError('El destino cambió desde la revisión.')
   self.features.organizer_preflight(ws,plan['moves'])
   try:
    for index,(source,dest) in enumerate(plan['moves']):
     if event.is_set():raise CancelledError()
     target(ws,source.relative_to(ws.root).as_posix());target(ws,dest.relative_to(ws.root).as_posix(),False)
     if dest.exists():raise ValueError('El destino acaba de cambiar: '+dest.name)
     missing=[];parent=dest.parent
     while not parent.exists():missing.append(parent);parent=parent.parent
     for parent in reversed(missing):parent.mkdir();created.append(parent)
     source.rename(dest);completed.append((source,dest))
     self.features.hilo.report(event,f'Moviendo {index+1} de {len(plan["moves"])}')
    if event.is_set():raise CancelledError()
    for folder in sorted(set(plan['empty']),key=lambda p:len(p.parts),reverse=True):
     if folder.exists() and not any(folder.iterdir()):folder.rmdir();removed.append(folder)
   except BaseException:
    for folder in reversed(removed):folder.mkdir(parents=True,exist_ok=True)
    for source,dest in reversed(completed):dest.rename(source)
    for folder in reversed(created):folder.rmdir()
    raise
  mappings=[{'oldPath':a.relative_to(ws.root).as_posix(),'path':b.relative_to(ws.root).as_posix()} for a,b in completed]
  self.features.organizer_changed(ws,mappings)
  receipt=None
  if completed:
   receipt=uuid.uuid4().hex
   with self.lock:
    self.receipts[receipt]={'workspace':str(ws.root),'moves':completed,'removed':removed,'created':created,
      'identities':{str(b):self.identity(b) for _,b in completed},'task':None,'undone':False}
    while len(self.receipts)>16:self.receipts.pop(next(iter(self.receipts)))
  return {'moved':mappings,'foldersMerged':len(removed),'undoReceipt':receipt}
 def identity(self,path):
  stat=path.stat();return [stat.st_dev,stat.st_ino,path.is_dir()]
 def undo(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de deshacer un movimiento.')
  with self.lock:
   receipt=self.receipts.get(body.get('receipt'))
   if not receipt or receipt['workspace']!=str(ws.root):raise ValueError('Este movimiento ya no está disponible para deshacer en esta sesión.')
   if receipt['task'] and self.features.hilo.jobs.get(receipt['task']['job'],{}).get('state') not in ('failed','cancelled'):return receipt['task']
   receipt['task']=self.features.hilo.submit('Deshacer movimiento de archivos',lambda event:self.revert(ws,receipt,event),workspace=str(ws.root),priority=-5)
   return receipt['task']
 def revert(self,ws,receipt,event):
  """Reverse identities and paths, preserving edits made since the move."""
  completed=[];restored=[];pruned=[]
  with ws.lock:
   if not ws.trusted:raise PermissionError('El proyecto ya no está autorizado.')
   if receipt['undone']:raise ValueError('Este movimiento ya se deshizo.')
   reverse=[(b,a) for a,b in reversed(receipt['moves'])]
   # Inspect descendants too: never carry a newly added link outside the project.
   self.inventory(ws,[b for b,_ in reverse])
   for current,original in reverse:
    target(ws,original.relative_to(ws.root).as_posix(),False)
    if self.identity(current)!=receipt['identities'][str(current)]:raise ValueError('Un archivo movido fue sustituido. No se puede deshacer sobre otra revisión.')
    if original.exists():raise ValueError('La ubicación original está ocupada: '+original.relative_to(ws.root).as_posix())
   if any(folder.exists() for folder in receipt['removed']):raise ValueError('Una carpeta original se ha vuelto a crear. Revisa el destino antes de deshacer.')
   self.features.organizer_preflight(ws,reverse)
   try:
    for folder in reversed(receipt['removed']):
     target(ws,folder.relative_to(ws.root).as_posix(),False);folder.mkdir();restored.append(folder)
    for index,(current,original) in enumerate(reverse):
     if event.is_set():raise CancelledError()
     if original.exists():raise ValueError('La ubicación original acaba de cambiar.')
     current.rename(original);completed.append((current,original))
     self.features.hilo.report(event,f'Restaurando {index+1} de {len(reverse)}')
    if event.is_set():raise CancelledError()
    for folder in reversed(receipt['created']):
     if folder.is_dir() and not any(folder.iterdir()):folder.rmdir();pruned.append(folder)
   except BaseException:
    for folder in reversed(pruned):folder.mkdir()
    for current,original in reversed(completed):original.rename(current)
    for folder in reversed(restored):folder.rmdir()
    raise
   receipt['undone']=True
  mappings=[{'oldPath':a.relative_to(ws.root).as_posix(),'path':b.relative_to(ws.root).as_posix()} for a,b in completed]
  self.features.organizer_changed(ws,mappings)
  return {'moved':mappings,'undone':True}
