"""On-demand tool discovery in the selected station, without compiling a project."""
import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
from concurrent.futures import CancelledError
from .runtime_paths import find_tool
from .runtimes import language,TOOLS,LABELS

def inspect(features,ws,path,event):
 if not ws.trusted:raise PermissionError('Autoriza el proyecto para comprobar sus herramientas.')
 file=ws.resolve(path);lang=language(path,features.runtimes.config['languages'])
 if not lang:raise ValueError('Configura un perfil para la extensión de este archivo.')
 destination=features.execution.selected(ws);profile=features.runtimes.config['languages'].get(lang,{})
 custom=bool(profile.get('build') or profile.get('run'));required=[]
 if custom:
  required=list(dict.fromkeys(argv[0] for key in ('check','build','run') if (argv:=profile.get(key)) and not argv[0].startswith('${target}')))
 else:
  required={'python':['python' if destination['kind']=='local' else 'python3'],'c':['gcc'],'cpp':['g++'],'java':['javac','java'],'nc':['ncc'],'asm':['nasm','gcc'] if file.suffix.lower()=='.asm' else ['gcc']}.get(lang,list(TOOLS.get(lang,())))
 signature=hashlib.sha256(json.dumps(features.runtimes.config,sort_keys=True).encode()).hexdigest()
 def discover():
  if destination['kind']=='local':
   rows=[]
   for tool in required:
    if tool=='python' and not custom:
     from .foundation import python_command
     executable=python_command(ws,features.runtimes.config.get('tools'))[0]
    else:
     executable=find_tool(tool,features.runtimes.config.get('tools'))
     if not executable and not custom and tool in ('gcc','g++'):executable=find_tool('clang' if tool=='gcc' else 'clang++',features.runtimes.config.get('tools'))
    rows.append({'name':tool,'available':bool(executable),'path':str(executable) if executable else None})
   return rows
  if destination['kind']!='wsl':return [{'name':tool,'available':None,'path':None} for tool in required]
  # Fixed shell syntax with individually quoted tool names. Discovery never
  # expands a configured run/build command or invokes a compiler.
  script='\n'.join("printf '%s\\t' "+str(i)+'; command -v '+shlex.quote(tool)+" || printf '\\n'" for i,tool in enumerate(required))
  result=subprocess.run([destination['executable'],'--distribution',destination['distribution'],'--exec','sh','-lc',script],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=8,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  if result.returncode:raise ValueError('No se pudo consultar WSL: '+result.stderr[-1000:])
  # Use one marker per tool so missing tools cannot shift the remaining rows.
  rows=[];found_tools={key:value for line in result.stdout.splitlines() if '\t' in line for key,_,value in [line.partition('\t')]}
  for i,tool in enumerate(required):
   # Paths may contain spaces; do not split shell output into words.
   found=found_tools.get(str(i))
   rows.append({'name':tool,'available':bool(found),'path':found})
  return rows
 if event.is_set():raise CancelledError()
 rows=features.hilo.cached(('readiness',str(ws.root),path,destination['id'],signature,getattr(ws,'environment_path',None)),discover,ttl=15,cancel=event)
 known=all(row['available'] is not None for row in rows)
 adapter=profile.get('debug',{}).get('adapter')
 return {'path':path,'language':lang,'label':LABELS.get(lang,lang),'target':{k:destination[k] for k in ('id','label','kind')},'tools':rows,'ready':all(row['available'] for row in rows) if known else None,'custom':custom,'debugger':{'configured':bool(adapter) or lang in ('python','java','javascript','typescript'),'command':adapter or [],'scope':'La depuración DAP se comprueba en Este equipo; no se deduce del compilador.'},'checkedAt':time.time(),'notice':'Herramientas localizadas en el destino; esta comprobación no compila ni ejecuta el programa.' if known else 'SSH requiere comprobar las herramientas en la estación remota. No se ha supuesto que las del anfitrión estén disponibles.'}

def submit(features,ws,body):
 path=body.get('path','');ws.resolve(path)
 return features.hilo.submit('Comprobar herramientas · '+Path(path).name,lambda event:inspect(features,ws,path,event),workspace=ws.root,key='readiness:'+path+':'+features.execution.selected(ws)['id'],priority=0)
