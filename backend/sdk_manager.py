"""Optional SDK components, verified local packages and reusable prepared roots."""
from pathlib import Path
import hashlib,json,os,shutil,stat,sys,tempfile,threading,zipfile
from .preferences import atomic_json
from . import foundation

class SDKManager:
 def __init__(self,features):
  self.features=features;self.directory=features.prefs.directory/'sdks';self.directory.mkdir(exist_ok=True);self.index=self.directory/'roots.json';self.lock=threading.RLock()
  try:self.config=json.loads(self.index.read_text(encoding='utf-8'))
  except (OSError,ValueError):self.config={'roots':[]}
  if self.config.get('roots'):foundation.set_sdk_roots(self.config['roots'])
 def status(self):
  groups=[];seen=set()
  for root in foundation.roots():
   try:data=foundation.read_index(root)
   except (OSError,ValueError):continue
   root=root.resolve()
   if str(root) in seen:continue
   seen.add(str(root));tools={name:str((root/path).resolve()) for name,path in data.get('tools',{}).items() if isinstance(path,str) and (root/path).resolve().is_relative_to(root) and (root/path).is_file()}
   groups.append({'directory':str(root),'managed':str(root) in self.config.get('roots',[]),'components':data.get('components',[]),'tools':tools})
  return {'roots':groups,'packagesDirectory':str(self.directory),'format':'zenit-sdk-1','platform':sys.platform}
 def activate(self,directory):
  if not isinstance(directory,str) or not Path(directory).is_absolute():raise ValueError('Selecciona una carpeta SDK absoluta.')
  root=Path(directory).resolve();data=foundation.read_index(root)
  if data.get('platform') not in (None,sys.platform):raise ValueError('Este SDK pertenece a otro sistema operativo.')
  for name,path in data.get('tools',{}).items():
   if not isinstance(path,str) or not (root/path).resolve().is_relative_to(root) or not (root/path).is_file():raise ValueError('El SDK contiene una herramienta ausente o una ruta externa: '+str(name))
  if not data.get('tools'):raise ValueError('Este índice no contiene herramientas.')
  with self.lock:
   candidates=[str(root),*[p for p in self.config.get('roots',[]) if p!=str(root)]]
   if len(candidates)>16:raise ValueError('Desactiva un SDK antes de añadir otro.')
   self.config={'roots':candidates};atomic_json(self.index,self.config);foundation.set_sdk_roots(candidates);self.features.hilo.invalidate()
  self.features.hilo.emit('sdk.changed',directory=str(root));return self.status()
 def deactivate(self,directory):
  with self.lock:
   self.config={'roots':[p for p in self.config.get('roots',[]) if p!=directory]};atomic_json(self.index,self.config);foundation.set_sdk_roots(self.config['roots']);self.features.hilo.invalidate()
  self.features.hilo.emit('sdk.changed',directory=directory)
  return self.status()
 def install(self,path,event=None):
  if not isinstance(path,str) or not Path(path).is_absolute():raise ValueError('Selecciona un paquete SDK local.')
  source=Path(path)
  if source.stat().st_size>4*1024**3:raise ValueError('Paquete SDK demasiado grande.')
  with zipfile.ZipFile(source) as archive:
   names=archive.namelist()
   if len(names)!=len(set(names)) or len(names)>60000:raise ValueError('Paquete SDK ambiguo o demasiado grande.')
   metadata=archive.getinfo('sdk-package.json')
   if metadata.file_size>2_000_000:raise ValueError('Manifiesto demasiado grande.')
   manifest=json.loads(archive.read(metadata))
   if manifest.get('schema')!=1 or manifest.get('platform')!=sys.platform:raise ValueError('Formato o plataforma SDK incompatible.')
   files=manifest.get('files')
   if not isinstance(files,dict) or not files or set(names)!={'sdk-package.json',*files}:raise ValueError('El paquete no coincide con su manifiesto.')
   size=0
   for name in files:
    if not isinstance(name,str) or '\\' in name or ':' in name or '\x00' in name or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Ruta SDK no válida.')
    item=archive.getinfo(name);size+=item.file_size
    if stat.S_ISLNK(item.external_attr>>16) or item.flag_bits&1 or item.is_dir() or size>12*1024**3:raise ValueError('El paquete contiene enlaces, cifrado o demasiados datos.')
   digest=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:24];target=self.directory/digest
   if target.is_symlink() or getattr(target,'is_junction',lambda:False)():raise ValueError('El SDK de destino es un enlace.')
   if target.exists():
    # Reusing a component must not trust files modified since its first import.
    for name,expected in files.items():
     if event is not None and event.is_set():raise ValueError('Instalación cancelada.')
     file=target/name
     if not file.resolve().is_relative_to(target) or file.is_symlink() or not file.is_file():raise ValueError('El SDK preparado contiene una ruta no válida: '+name)
     digest_file=hashlib.sha256()
     with file.open('rb') as stream:
      for block in iter(lambda:stream.read(1024*1024),b''):digest_file.update(block)
     if digest_file.hexdigest()!=expected:raise ValueError('El componente preparado cambió. Desactívalo y prepara una copia nueva: '+name)
   if not target.exists():
    with tempfile.TemporaryDirectory(prefix='.prepare-',dir=self.directory) as tmp:
     stage=Path(tmp)
     for name,expected in files.items():
      if event is not None and event.is_set():raise ValueError('Instalación cancelada.')
      dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);checksum=hashlib.sha256()
      with archive.open(name) as stream,dest.open('wb') as output:
       while chunk:=stream.read(1024*1024):checksum.update(chunk);output.write(chunk)
      if checksum.hexdigest()!=expected:raise ValueError('La verificación SHA-256 ha fallado: '+name)
      if os.name!='nt' and archive.getinfo(name).external_attr>>16&0o111:dest.chmod(dest.stat().st_mode|0o111)
     foundation.read_index(stage)
     os.replace(stage,target)
   return self.activate(str(target))
