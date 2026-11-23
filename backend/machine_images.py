"""Verified local installation media and sparse per-project QEMU machines."""
from concurrent.futures import CancelledError
import hashlib,json,os,re,shutil,subprocess,threading,time,uuid
from pathlib import Path
from .preferences import atomic_json
from .terminals import child_environment

CATALOG=[
 {'id':'arch','name':'Arch Linux','url':'https://archlinux.org/download/','note':'Usa la imagen del SDK o importa un disco QCOW2 independiente o su ISO oficial.'},
 {'id':'debian','name':'Debian','url':'https://cloud.debian.org/images/cloud/','note':'Las imágenes cloud configuradas para consola serie pueden abrirse dentro de Zénit.'},
 {'id':'kali','name':'Kali Linux','url':'https://www.kali.org/get-kali/','note':'Importa una imagen QEMU o una ISO del distribuidor. El modo gráfico abre QEMU en otra ventana.'},
 {'id':'windows11','name':'Windows 11','url':'https://www.microsoft.com/software-download/windows11','note':'Importa tu medio con licencia. Esta edición del laboratorio usa QEMU x86-64 y detecta la aceleración disponible; no configura TPM ni Secure Boot.'},
 {'id':'windows7','name':'Windows 7','url':'https://www.microsoft.com/windows','note':'Importa tu medio con licencia o conecta una VM existente por SSH. No se incluyen imágenes.'},
 {'id':'macos','name':'macOS','url':'https://support.apple.com/macos','note':'Conecta un Mac o una VM en hardware Apple mediante SSH; no se ofrece arranque local macOS.'},
]

class MachineImages:
 def __init__(self,features):
  self.features=features;self.root=features.prefs.directory/'machines/images';self.root.mkdir(parents=True,exist_ok=True);self.index=self.root/'index.json';self.lock=threading.RLock();self.sessions={}
  try:self.images=json.loads(self.index.read_text('utf-8'))
  except (OSError,ValueError):self.images=[]
 def snapshot(self,ws):
  base=self.features.machines.vm_base()
  return {'images':self.images,'catalog':CATALOG,'tools':{'qemu':bool(base.get('qemu')),'qemu-img':bool(base.get('qimg'))},'ready':bool(base.get('qemu') and base.get('qimg')),'sessions':[dict(p,saved=p.get('saved'),running=bool((terminal:=self.features.terminals.sessions.get(self.features.machines.active.get(p['id']))) and not terminal.closed)) for p in self.sessions.values() if p['workspace']==str(ws.root)],
   'saved':[p.name for p in ws.root.glob('*.tern') if p.is_file() and not p.is_symlink() and self.is_descriptor(p)][:100]}
 @staticmethod
 def is_descriptor(file):
  try:return file.stat().st_size<32000 and json.loads(file.read_text('utf-8')).get('type')=='zenit-machine'
  except (OSError,ValueError):return False
 def command(self,argv,event,timeout=900):
  task=self.features.app.runner.start([argv],self.root,timeout=timeout)
  job=self.features.app.runner.jobs[task['job']]
  job.background=True
  while not job.done:
   if event.wait(.1):job.cancel()
  if event.is_set():raise CancelledError()
  if job.code:raise ValueError(job.output[-2000:] or 'QEMU no completó la operación.')
  return job.output
 def image_file(self,image):
  file=(self.root/image['file']).resolve()
  if file.parent!=self.root.resolve() or not file.is_file() or file.is_symlink():raise ValueError('El medio no está disponible en la biblioteca.')
  return file
 def import_image(self,ws,body,event):
  file=Path(body.get('path','')).expanduser()
  if not file.is_absolute() or not file.is_file() or file.is_symlink() or file.suffix.lower() not in ('.iso','.qcow2'):raise ValueError('Selecciona una ISO o un QCOW2 independiente.')
  expected=body.get('sha256','').lower();name=str(body.get('name') or file.stem).strip()[:80];system=body.get('system','linux')
  if system not in ('linux','windows11','windows7') or not name:raise ValueError('Selecciona Linux o Windows y un nombre para el medio.')
  if not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Introduce el SHA-256 del distribuidor o del medio local que quieres importar.')
  if file.stat().st_size>shutil.disk_usage(self.root).free-256*1024*1024:raise ValueError('No hay espacio para copiar el medio a la biblioteca.')
  identity=uuid.uuid4().hex;target=self.root/(identity+file.suffix.lower());partial=self.root/(identity+'.part');value=hashlib.sha256()
  try:
   self.features.hilo.report(event,'Copiando y verificando medio')
   with file.open('rb') as source,partial.open('xb') as output:
    while chunk:=source.read(1024*1024):
     if event.is_set():raise CancelledError()
     output.write(chunk);value.update(chunk)
   if value.hexdigest()!=expected:raise ValueError('El SHA-256 no coincide. Se conserva el original y se descarta la copia incompleta.')
   if file.suffix.lower()=='.qcow2':
    qimg=self.features.machines.vm_base().get('qimg')
    if not qimg:raise ValueError('Prepara qemu-img en el SDK para inspeccionar el disco.')
    raw=self.command([qimg,'info','--output=json',str(partial)],event,30).partition('\n')[2]
    data=json.JSONDecoder().raw_decode(raw.lstrip())[0]
    specific=data.get('format-specific',{}).get('data',{})
    if data.get('format')!='qcow2' or data.get('backing-filename') or specific.get('data-file'):raise ValueError('Importa un QCOW2 independiente, sin archivos base ni datos externos.')
   partial.replace(target)
   image={'id':identity,'name':name,'system':system,'format':'iso' if file.suffix.lower()=='.iso' else 'qcow2','file':target.name,'sha256':expected,'bytes':target.stat().st_size,'imported':time.time()}
   with self.lock:self.images=[*self.images,image];atomic_json(self.index,self.images)
   return {'image':image}
  finally:partial.unlink(missing_ok=True)
 def directory(self,ws,identity):
  return self.features.tern.directory(ws,identity)
 def owned(self,ws,identity):
  directory=self.directory(ws,identity);marker=directory/'machine-owner.json'
  if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text('utf-8')).get('id')!=identity:raise ValueError('El disco no pertenece a esta máquina de Zénit.')
  return directory
 def create(self,ws,body,event):
  with self.lock:
   if len(self.sessions)>=8:raise ValueError('Cierra una sesión antes de crear otra; el límite es ocho.')
  image=next((i for i in self.images if i['id']==body.get('image')),None)
  if not image:raise ValueError('Selecciona un medio importado.')
  memory=body.get('memory',2048);cpus=body.get('cpus',1);size=body.get('size',32);display=body.get('display','serial')
  if memory not in (1024,2048,4096,8192) or cpus not in (1,2,4) or size not in (16,32,64,128) or display not in ('serial','graphic'):raise ValueError('Recursos de máquina no válidos.')
  if image['system']=='windows11':raise ValueError('Windows 11 requiere un perfil TPM/UEFI que este laboratorio todavía no prepara. Conecta una VM existente por SSH.')
  import psutil
  used=[s for s in self.sessions.values() if self.features.machines.active.get(s['id'])]
  if memory+sum(s['memory'] for s in used)>psutil.virtual_memory().available/1024**2*.8:raise ValueError('No hay suficiente RAM disponible para esta reserva.')
  base=self.features.machines.vm_base();qimg=base.get('qimg')
  if not qimg or not base.get('qemu'):raise ValueError('Prepara QEMU en el SDK.')
  source=self.image_file(image);identity=uuid.uuid4().hex;directory=self.directory(ws,identity);directory.mkdir(parents=True)
  atomic_json(directory/'machine-owner.json',{'id':identity,'workspace':str(ws.root)})
  disk=directory/'disk.qcow2'
  try:
   argv=[qimg,'create','-f','qcow2',*(['-F','qcow2','-b',str(source)] if image['format']=='qcow2' else []),str(disk),str(size)+'G']
   self.command(argv,event,30)
   profile={'id':identity,'name':str(body.get('name') or image['name'])[:80],'type':'image','workspace':str(ws.root),'disk':str(disk),'seed':str(source) if image['format']=='iso' else None,'memory':memory,'cpus':cpus,'display':display,'image':image['id'],'system':image['system'],'size':size,'saved':None}
   with self.lock:self.sessions[identity]=profile
   return {'machine':profile}
  except BaseException:
   if self.owned(ws,identity)==directory:shutil.rmtree(directory)
   raise
 def get(self,ws,identity):
  profile=self.sessions.get(identity)
  if not profile or profile['workspace']!=str(ws.root):raise ValueError('Máquina desconocida para este proyecto.')
  self.owned(ws,identity);return profile
 def start(self,ws,identity):
  p=self.get(ws,identity)
  # Machines.start reuses an existing terminal before checking resources for a
  # new guest. Reopening its console must not reserve a second machine's RAM.
  return self.features.machines.start(ws,identity,profile=p)
 def save(self,ws,body):
  p=self.get(ws,body.get('id'));name=body.get('file','')
  if not isinstance(name,str) or not re.fullmatch(r'[\w -]{1,80}\.tern',name):raise ValueError('Usa un nombre de archivo .tern en la raíz del proyecto.')
  file=ws.resolve(name,must_exist=False)
  if file.exists() and p.get('saved')!=name:raise FileExistsError('Ese descriptor ya existe y se conserva.')
  image=next(i for i in self.images if i['id']==p['image'])
  atomic_json(file,{'schema':1,'type':'zenit-machine','id':p['id'],'name':p['name'],'image':{'sha256':image['sha256'],'format':image['format'],'system':image['system']},'memory':p['memory'],'cpus':p['cpus'],'display':p['display'],'size':p['size']});p['saved']=name
  return {'file':name,'note':'El descriptor conserva esta sesión y su disco en el proyecto. En otro equipo también necesitas la imagen base y el disco; no es una ISO reducida.'}
 def reopen(self,ws,body):
  file=ws.resolve(body.get('file',''))
  if not self.is_descriptor(file):raise ValueError('Selecciona un descriptor de máquina de esta biblioteca.')
  data=json.loads(file.read_text('utf-8'));directory=self.owned(ws,data.get('id'))
  if data['id'] in self.sessions:return {'machine':self.get(ws,data['id'])}
  image=next((i for i in self.images if i['sha256']==data['image']['sha256']),None)
  if not image:raise ValueError('Falta el medio base. Impórtalo en la biblioteca con el mismo SHA-256 antes de continuar.')
  if not (directory/'disk.qcow2').is_file():raise ValueError('Falta el disco de la sesión; el descriptor no contiene sus bytes.')
  profile={'id':data['id'],'type':'image','workspace':str(ws.root),'disk':str(directory/'disk.qcow2'),'seed':str(self.image_file(image)) if image['format']=='iso' else None,'image':image['id'],'system':image['system'],'saved':file.name,**{k:data[k] for k in ('name','memory','cpus','display','size')}}
  if profile['memory'] not in (1024,2048,4096,8192) or profile['cpus'] not in (1,2,4) or profile['display'] not in ('serial','graphic'):raise ValueError('Recursos del descriptor no válidos.')
  self.sessions[profile['id']]=profile;return {'machine':profile}
 def stop(self,ws,identity):self.get(ws,identity);self.features.machines.stop(identity);return {'stopped':True}
 def export(self,ws,body,event):
  p=self.get(ws,body.get('id'));session=self.features.terminals.sessions.get(self.features.machines.active.get(p['id']))
  if session and not session.closed:raise ValueError('Detén la máquina antes de exportar un disco consistente.')
  name=body.get('file','')
  if not isinstance(name,str) or not re.fullmatch(r'[\w -]{1,80}\.qcow2',name):raise ValueError('Elige un archivo .qcow2 nuevo en la raíz del proyecto.')
  target=ws.resolve(name,must_exist=False)
  if target.exists():raise FileExistsError('El archivo de exportación ya existe.')
  partial=self.owned(ws,p['id'])/('export-'+uuid.uuid4().hex+'.qcow2')
  try:
   self.command([self.features.machines.vm_base()['qimg'],'convert','-c','-O','qcow2',p['disk'],str(partial)],event)
   # Link is exclusive: never replace a concurrent user's file.
   os.link(partial,target);return {'file':name,'bytes':target.stat().st_size,'independent':True,'note':'Disco comprimido sin base externa. Necesitas un sistema instalado para arrancarlo.'}
  finally:partial.unlink(missing_ok=True)
 def discard(self,ws,identity):
  p=self.get(ws,identity)
  if p['saved']:raise ValueError('Esta máquina está guardada; se conserva su disco. Cierra su consola para detenerla.')
  self.stop(ws,identity);directory=self.owned(ws,identity);shutil.rmtree(directory);self.sessions.pop(identity,None);return {'removed':True}
 def close_workspace(self,ws):
  for p in list(self.sessions.values()):
   if p['workspace']!=str(ws.root):continue
   try:
    self.stop(ws,p['id'])
    if not p['saved']:self.discard(ws,p['id'])
    else:self.sessions.pop(p['id'],None)
   except Exception as error:self.features.hilo._failure('machine-close',error)
