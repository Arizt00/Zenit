"""Installer handoff: wait for the editor, preserve recovery metadata, install, restart."""
import hashlib,json,os,time,zipfile
from pathlib import Path
from .preferences import atomic_json

def digest(file):
 value=hashlib.sha256()
 with Path(file).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
 return value.hexdigest()

def read_request(path):
 path=Path(path).resolve()
 if path.stat().st_size>32000:raise ValueError('Solicitud demasiado grande.')
 data=json.loads(path.read_text('utf-8'));profile=Path(data['profile']).resolve();target=Path(data['target']).resolve()
 if path.parent!=profile/'updates' or len(profile.parts)<3 or len(target.parts)<3 or target==Path(target.anchor):raise ValueError('Rutas de actualización no válidas.')
 if not (target/'installation.json').is_file() or not (target/'Zenit.exe').is_file():raise ValueError('No se encontró la instalación que se va a actualizar.')
 if type(data.get('pid')) is not int or data['pid']<=0 or abs(time.time()-data.get('created',0))>600:raise ValueError('Solicitud caducada.')
 return data,profile,target

def backup_metadata(profile):
 """Copy recovery/configuration metadata; project source and SDK payloads stay in place."""
 folder=profile/'updates/backups';folder.mkdir(parents=True,exist_ok=True)
 output=folder/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns())+'.zip');total=0
 with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
  for directory,dirs,files in os.walk(profile,followlinks=False):
   dirs[:]=[d for d in dirs if d not in ('updates','downloads','cache','logs','node_modules','packages','sdk-cache') and not (Path(directory)/d).is_symlink()]
   for name in files:
    file=Path(directory)/name
    if file.is_symlink() or file.suffix.lower() not in ('.json','.jsonl','.tern'):continue
    size=file.stat().st_size
    if size>52*1024*1024 or total+size>256*1024*1024:raise ValueError('La copia de recuperación supera su límite. La instalación no se ha iniciado.')
    archive.write(file,file.relative_to(profile));total+=size
 return output

def wait_for_editor(data,timeout=120):
 import psutil
 try:
  process=psutil.Process(data['pid'])
  if abs(process.create_time()-data['processCreated'])>1:raise ValueError('El proceso de Zénit cambió; vuelve a preparar la actualización.')
  process.wait(timeout=timeout)
 except psutil.NoSuchProcess:pass

def apply_update(request,installer_factory,*,wait=wait_for_editor,launch=None):
 data,profile,target=read_request(request);receipt=profile/'updates/install-result.json';exited=False
 try:
  atomic_json(receipt,{'state':'waiting','request':Path(request).name,'version':data['version']})
  wait(data)
  exited=True
  if digest(data['installer'])!=data['sha256']:raise ValueError('El instalador cambió después de verificarse.')
  backup=backup_metadata(profile)
  atomic_json(receipt,{'state':'installing','version':data['version'],'backup':str(backup)})
  installer=installer_factory(target=target)
  previous=json.loads((target/'installation.json').read_text('utf-8'));integrations=previous.get('integrations',{})
  installer._install({'locale':data.get('locale','en'),'packages':[],**{key:bool(integrations.get(key,default)) for key,default in (('shortcuts',True),('register',True),('desktop',False))}})
  result=installer.status()
  if result['status']!='finished':raise ValueError(result.get('message') or 'No se completó la instalación.')
  atomic_json(receipt,{'state':'installed','version':data['version'],'backup':str(backup),'finished':time.time()})
 except Exception as error:
  atomic_json(receipt,{'state':'error','request':Path(request).name,'version':data['version'],'error':str(error)[:1000]})
  raise
 finally:
  # Relaunch only after the original editor has exited. On installation failure
  # the stable launcher still points at the previous usable payload.
  state=json.loads(receipt.read_text('utf-8'))
  if exited and launch:launch(target/'Zenit.exe',data['workspace'])
