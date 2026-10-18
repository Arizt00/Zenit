"""One workspace destination for runtime plans; never silently falls back to host."""
from pathlib import Path,PurePosixPath
import hashlib,os,re,shlex,subprocess,sys
from .runtime_paths import find_tool

class ExecutionTargets:
 def __init__(self,features):self.features=features
 def _wsl(self):
  exe=find_tool('wsl') if os.name=='nt' else None
  if not exe:return []
  try:
   result=subprocess.run([exe,'--list','--quiet'],capture_output=True,timeout=4,creationflags=0x08000000)
   if result.returncode:return []
   raw=result.stdout;text=raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8',errors='replace')
   names=[line.strip() for line in text.splitlines()]
   return [{'id':'wsl:'+name,'label':'WSL · '+name,'kind':'wsl','distribution':name,'executable':exe,'available':True,'system':'linux'} for name in names if re.fullmatch(r'[\w .-]{1,80}',name)]
  except (OSError,subprocess.SubprocessError):return []
 def inventory(self,ws,refresh=False):
  if refresh:self.features.hilo.invalidate()
  targets=[{'id':'local','label':'Este equipo','kind':'local','available':True,'system':sys.platform}]
  targets+=self.features.hilo.cached('wsl-targets',self._wsl,ttl=60)
  ssh=find_tool('ssh')
  for p in self.features.machines.profiles:
   targets.append({'id':'ssh:'+p['id'] if p.get('mode')=='ssh' else 'vm:'+p['id'],'label':p['name'],'kind':'ssh' if p.get('mode')=='ssh' else 'vm','available':bool(ssh and p.get('mode')=='ssh' and p['type']!='windows7'),'system':'macos' if p['type']=='macos' else 'linux','note':None if p.get('mode')=='ssh' else 'Consola disponible en Lantern; conecta la VM por SSH para ejecutar archivos.'})
  selected=self.features.workbenches.snapshot(ws).get('target','local')
  if selected not in {x['id'] for x in targets}:targets.append({'id':selected,'label':'Destino no disponible','kind':'unavailable','available':False})
  return {'selected':selected,'targets':targets,'options':self.features.workbenches.snapshot(ws).get('targetOptions',{})}
 def select(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto para cambiar su ejecución.')
  key=body.get('id');target=next((x for x in self.inventory(ws)['targets'] if x['id']==key),None)
  if not target or not target['available']:raise ValueError('El destino no está preparado para ejecutar archivos.')
  options={}
  if target['kind']=='ssh':
   folder=body.get('directory','')
   if not isinstance(folder,str) or not folder.startswith('/') or '\x00' in folder or '\n' in folder or len(folder)>2048:raise ValueError('Indica la carpeta absoluta del proyecto en la estación remota.')
   options={'directory':str(PurePosixPath(folder))}
  old=self.features.workbenches.snapshot(ws).get('target','local')
  if old!=key:self.features.lantern.stop()
  self.features.workbenches.set_target(ws,key,options)
  self.features.hilo.emit('execution.target.changed',workspace=str(ws.root),target=key)
  return self.inventory(ws)
 def selected(self,ws):
  root=getattr(ws,'python_workspace',ws)
  key=self.features.workbenches.snapshot(root).get('target','local')
  if key=='local':return {'id':'local','kind':'local','label':'Este equipo','available':True}
  target=next((x for x in self.inventory(root)['targets'] if x['id']==key),None)
  if not target or not target['available']:raise ValueError('El destino de ejecución no está disponible. Selecciona otro destino.')
  return target
 def require_local(self,ws,feature):
  if self.selected(ws)['kind']!='local':raise ValueError(feature+' requiere el destino Este equipo en esta versión. La ejecución remota de archivos sigue disponible.')
 @staticmethod
 def linux_path(path):
  value=str(path).replace('\\','/')
  if re.match(r'^[A-Za-z]:/',value):return '/mnt/'+value[0].lower()+value[2:]
  if not value.startswith('/'):raise ValueError('La ruta no puede compartirse con Linux.')
  return value
 def plan(self,ws,name,check=False):
  target=self.selected(ws)
  if target['kind']=='local':return None
  from .runtimes import language
  file=ws.resolve(name);lang=language(name)
  if target['kind']=='wsl':folder=self.linux_path(ws.root);source=self.linux_path(file)
  else:
   original=getattr(ws,'python_workspace',ws)
   if original.root!=ws.root:raise ValueError('Los búferes temporales de Lantern necesitan un destino local o WSL. Guarda el archivo para ejecutarlo por SSH.')
   folder=self.features.workbenches.snapshot(original).get('targetOptions',{}).get('directory')
   if not folder:raise ValueError('Configura la carpeta del proyecto remoto.')
   source=str(PurePosixPath(folder)/file.relative_to(ws.root).as_posix())
  identity=hashlib.sha256(name.encode()).hexdigest()[:12];output=str(PurePosixPath(folder)/'.lumen/run'/identity/'program')
  parent=str(PurePosixPath(output).parent);commands=[]
  profile=self.features.runtimes.config.get('languages',{}).get(lang,{})
  if any(k in profile for k in ('run','build','check')):
   def expand(argv):
    values={'${workspaceFolder}':folder,'${file}':source,'${fileDirname}':str(PurePosixPath(source).parent),'${fileBasenameNoExtension}':file.stem,'${target}':output}
    out=[]
    for word in argv:
     for token,value in values.items():word=word.replace(token,value)
     if re.match(r'^[A-Za-z]:[\\/]',word):raise ValueError('El perfil usa herramientas Windows. Configura herramientas compatibles con el destino remoto.')
     out.append(word)
    return out
   for key in (('check',) if check else ('build','run')):
    if profile.get(key):commands.append(expand(profile[key]))
   if not commands:raise ValueError('El perfil no define esta acción para el destino remoto.')
  elif lang=='python':commands=[['python3','-m','py_compile',source]] if check else [['python3','-u',source]]
  elif lang in ('javascript','bash'):commands=[[{'javascript':'node','bash':'bash'}[lang],*(['--check'] if check and lang=='javascript' else ['-n'] if check else []),source]]
  elif lang in ('c','cpp'):
   commands=[[('gcc' if lang=='c' else 'g++'),'-g','-Wall','-Wextra','-std='+profile.get('standard','c17' if lang=='c' else 'c++20'),*(['-fsyntax-only'] if check else []),source,*([] if check else ['-o',output])]]
   if not check:commands.append([output])
  elif lang=='asm':
   text=file.read_text(encoding='utf-8-sig');nasm=file.suffix.lower()=='.asm'
   if re.search(r'\becall\b|\$(?:v[01]|a[0-3])\b',text):raise ValueError('Selecciona el motor educativo en el laboratorio ASM o configura un perfil remoto para esa arquitectura.')
   if nasm:
    from .nasm import target_system
    if target['system']!='linux' or target_system(text,'linux')!='linux':raise ValueError('Este perfil NASM remoto requiere Linux y código para su ABI.')
    bits='32' if re.search(r'(?im)^\s*\[?bits\s+32\b',text) else '64';obj=output+'.o';commands=[['nasm','-f','elf'+bits,'-I',str(PurePosixPath(source).parent)+'/',source,'-o',obj]]
    if not check:commands.append(['gcc',*(['-m32'] if bits=='32' else []),*(['-nostdlib','-no-pie','-Wl,-e,_start'] if re.search(r'(?im)^\s*global\s+_start\b',text) else []),obj,'-o',output]);commands.append([output])
   else:commands=[['gcc',*(['-fsyntax-only'] if check else []),source,*([] if check else ['-o',output])]]+([] if check else [[output]])
  elif lang=='rust':commands=[['rustc',source,'-o',output]]+([] if check else [[output]])
  elif lang=='go':commands=[['go','build','-o',output,source]]+([] if check else [[output]])
  else:raise ValueError('Configura un perfil de compilación remoto para '+str(lang)+'. No se ejecutará en el equipo local.')
  wrapped=[]
  for index,argv in enumerate(commands):
   script='cd '+shlex.quote(folder)+' && mkdir -p '+shlex.quote(parent)+' && '+('exec ' if index==len(commands)-1 else '')+shlex.join(argv)
   if target['kind']=='wsl':prefix=[target['executable'],'--distribution',target['distribution'],'--exec','sh','-lc',script]
   else:
    p=next(x for x in self.features.machines.profiles if 'ssh:'+x['id']==target['id']);prefix=[find_tool('ssh'),'-tt' if not check and index==len(commands)-1 else '-T','-p',str(p['port']),'-l',p['user'],p['host'],'sh -lc '+shlex.quote(script)]
   wrapped.append(prefix)
  return {'commands':wrapped,'executionTarget':{k:target[k] for k in ('id','label','kind')},'artifacts':{'created':[]}}
