"""Reviewed project kits and deduplicated build receipts for the shared runtime."""
import copy,hashlib,json,os,re,threading,time,uuid
from pathlib import Path
from .preferences import atomic_json
from .runtimes import language
from .runtime_paths import find_tool

KITS={
 'python':{'label':'Python','tools':['python'],'entry':'main.py','files':{
  'main.py':'def answer():\n    return 42\n\nif __name__ == "__main__":\n    print(answer())\n',
  'pyproject.toml':'[project]\nname = "zenit-project"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n',
  'tests/test_main.py':'import unittest\nfrom main import answer\n\nclass MainTest(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 42)\n'}},
 'c':{'label':'C','tools':['gcc'],'entry':'main.c','files':{
  'main.c':'#include <stdio.h>\n#include "main.h"\nint answer(void) { return 42; }\nint main(void) { printf("%d\\n", answer()); return 0; }\n',
  'main.h':'#ifndef ZENIT_MAIN_H\n#define ZENIT_MAIN_H\nint answer(void);\n#endif\n',
  'CMakeLists.txt':'cmake_minimum_required(VERSION 3.20)\nproject(zenit_project C)\nset(CMAKE_C_STANDARD 17)\nadd_executable(zenit_app main.c)\nenable_testing()\nadd_test(NAME smoke COMMAND zenit_app)\nset_tests_properties(smoke PROPERTIES PASS_REGULAR_EXPRESSION "42")\n'}},
 'cpp':{'label':'C++','tools':['g++'],'entry':'main.cpp','files':{
  'main.cpp':'#include <iostream>\n#include "main.hpp"\nint answer() { return 42; }\nint main() { std::cout << answer() << "\\n"; }\n',
  'main.hpp':'#pragma once\nint answer();\n',
  'CMakeLists.txt':'cmake_minimum_required(VERSION 3.20)\nproject(zenit_project CXX)\nset(CMAKE_CXX_STANDARD 20)\nadd_executable(zenit_app main.cpp)\nenable_testing()\nadd_test(NAME smoke COMMAND zenit_app)\nset_tests_properties(smoke PROPERTIES PASS_REGULAR_EXPRESSION "42")\n'}},
 'java':{'label':'Java','tools':['javac','java'],'entry':'Main.java','files':{
  'Main.java':'public final class Main {\n    public static int answer() { return 42; }\n    public static void main(String[] args) {\n        if (answer() != 42) throw new AssertionError("answer");\n        System.out.println(answer());\n    }\n}\n',
  'pom.xml':'<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>local.zenit</groupId><artifactId>zenit-project</artifactId><version>0.1.0</version><properties><maven.compiler.release>17</maven.compiler.release></properties><build><sourceDirectory>${project.basedir}</sourceDirectory></build></project>\n'}},
 'asm':{'label':'ASM · NASM x86-64','tools':['nasm','gcc'],'entry':'main.asm','files':{
  'main.asm':'bits 64\nglobal main\nsection .text\nmain:\n    mov eax, 0\n    ret\n',
  'README.txt':'NASM x86-64. El destino nativo se detecta como win64 o elf64. Para RISC-V/MIPS usa el laboratorio simulado y su toolchain.\n'}},
 'nc':{'label':'nC','tools':['ncc'],'entry':None,'files':{}},
}

class ProjectWorkflows:
 def __init__(self,features):self.features=features;self.lock=threading.RLock();self.plans={};self.active={};self.receipts={}
 def catalog(self,ws):
  config=self.features.runtimes.config.get('tools');kits=[]
  for ident,kit in KITS.items():
   tools=[{'name':name,'path':find_tool(name,config)} for name in kit['tools']]
   kits.append({'id':ident,'label':kit['label'],'tools':tools,'ready':all(t['path'] for t in tools),'entry':kit['entry']})
  return {'kits':kits,'workspace':str(ws.root),'history':self.history(ws),'target':self.features.workbenches.snapshot(ws).get('target','local')}
 def store(self,ws,plan):
  with self.lock:
   plan.update(id=uuid.uuid4().hex,workspace=str(ws.root),created=time.time());self.plans[plan['id']]=plan
   while len(self.plans)>24:self.plans.pop(next(iter(self.plans)))
  return self.public(plan)
 @staticmethod
 def public(plan):return {k:v for k,v in plan.items() if k not in ('workspace','task')}
 def get(self,ws,ident,kind):
  with self.lock:plan=self.plans.get(ident)
  if not plan or plan['workspace']!=str(ws.root) or plan['kind']!=kind or time.time()-plan['created']>1800:raise ValueError('El plan ha caducado. Vuelve a revisarlo.')
  return plan
 def scaffold_plan(self,ws,body):
  kit=KITS.get(body.get('language'));folder=body.get('folder','')
  if not kit or not isinstance(folder,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,59}',folder):raise ValueError('Elige un lenguaje y una carpeta nueva con nombre sencillo.')
  target=ws.resolve(folder,must_exist=False)
  if target.exists():raise ValueError('La carpeta ya existe; se conserva íntegra. Elige otra.')
  return self.store(ws,{'kind':'scaffold','language':body['language'],'folder':folder,'files':[{'path':folder+'/'+name,'content':content} for name,content in kit['files'].items()],
   'commands':[['ncc','package','init',folder,'--path',str(target)]] if body['language']=='nc' else []})
 def scaffold(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de preparar archivos.')
  plan=self.get(ws,body.get('plan'),'scaffold');target=ws.resolve(plan['folder'],must_exist=False)
  with ws.lock:
   if target.exists():raise ValueError('La carpeta cambió desde la revisión. Se conserva.')
   if plan['language']=='nc':
    ncc=find_tool('ncc',self.features.runtimes.config.get('tools'))
    if not ncc:raise ValueError('Prepara el SDK nC antes de crear su paquete nativo.')
    target.mkdir();task=self.features.app.runner.start([[ncc,'package','init',plan['folder'],'--path',str(target)]],ws.root,scheduler=self.features.hilo)
    return {'folder':plan['folder'],'task':task,'entry':None}
   target.mkdir();written=[]
   try:
    for item in plan['files']:ws.save(item['path'],item['content'],None,create=True);written.append(item['path'])
   except BaseException:
    # Retain partial files for review, never remove a user's concurrent edit.
    raise ValueError('Preparación incompleta; se conservan los archivos ya creados para revisarlos.')
  return {'folder':plan['folder'],'entry':plan['folder']+'/'+KITS[plan['language']]['entry'],'files':written}
 def fingerprints(self,ws,path):
  parent=ws.resolve(path).parent;result={};budget=4_000_000
  visited=0
  for folder,dirs,files in os.walk(parent,followlinks=False):
   dirs[:]=[d for d in dirs if d not in ('.lumen','.git','.venv','node_modules','build','target','__pycache__') and not (Path(folder)/d).is_symlink() and (Path(folder)/d).resolve().is_relative_to(ws.root)]
   for name in files:
    visited+=1;file=Path(folder)/name
    if len(result)>=250 or budget<=0 or visited>5000:raise ValueError('El conjunto de entradas supera el límite de este flujo. Usa un subproyecto más pequeño.')
    if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(ws.root):continue
    rel=file.relative_to(ws.root)
    if file.name.startswith('.env') or file.suffix.lower() not in ('.c','.h','.hpp','.cpp','.py','.java','.asm','.n','.nc','.json','.toml','.txt'):continue
    if file.stat().st_size>min(300000,budget):raise ValueError('Una entrada supera el límite del flujo revisable. Usa el ejecutor del proyecto para este archivo.')
    raw=file.read_bytes();budget-=len(raw);result[rel.as_posix()]=hashlib.sha256(raw).hexdigest()
  return result
 def plan(self,ws,body):
  action=body.get('action');path=body.get('path')
  if action not in ('check','build','run'):raise ValueError('Elige comprobar, compilar o ejecutar.')
  lang=language(path or '')
  if lang not in KITS:raise ValueError('Este flujo admite Python, C, C++, Java, nC y ASM.')
  plan=self.features.runtimes.plan(ws,path,check=action=='check' or action=='build' and lang=='python')
  commands=copy.copy(plan['commands'])
  remote=plan.get('executionTarget')
  if lang=='python' and action in ('check','build') and not remote:
   from .foundation import python_command
   commands=[[*python_command(ws,self.features.runtimes.config.get('tools')),'-c','import ast,pathlib,sys; ast.parse(pathlib.Path(sys.argv[1]).read_bytes())',str(ws.resolve(path))]]
  if action=='build' and lang!='python':
   if remote:raise ValueError('Este destino remoto no expone una compilación separada. Usa comprobar o ejecutar.')
   if len(commands)<2:raise ValueError('La configuración no ofrece una fase de compilación separada.')
   commands.pop()
  result=self.store(ws,{'kind':'execution','action':action,'path':path,'language':lang,'commands':commands,'cwd':str(plan.get('cwd',ws.root)),
   'fingerprints':self.fingerprints(ws,path),'target':remote or str(plan.get('target','local'))})
  # Keep BuildCommands and its exact-input compilation cache on the server.
  self.plans[result['id']]['commands']=commands
  return result
 def run(self,ws,body):
  if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de ejecutar el plan.')
  plan=self.get(ws,body.get('plan'),'execution')
  with self.lock:
   if plan.get('task'):return plan['task']
   old=self.features.app.runner.jobs.get(self.active.get(str(ws.root)))
   if old and not old.done:raise ValueError('Ya hay un flujo de proyecto en ejecución. Espera o cancélalo desde Tareas.')
   if self.fingerprints(ws,plan['path'])!=plan['fingerprints']:raise ValueError('Las entradas cambiaron desde la revisión. Genera otro plan.')
   task=self.features.app.runner.start(plan['commands'],Path(plan['cwd']),timeout=300,scheduler=self.features.hilo)
   self.active[str(ws.root)]=task['job'];plan['task']=task
   record={'id':task['job'],'action':plan['action'],'path':plan['path'],'language':plan['language'],'commands':list(plan['commands']),
    'inputs':plan['fingerprints'],'started':time.time(),'state':'running','output':''}
   rows=self.history(ws);rows.append(record);self.receipts[str(ws.root)]=rows[-24:];self.persist(ws)
   return task
 def persist(self,ws):atomic_json(ws.private_dir('workflows')/'receipts.json',self.receipts[str(ws.root)])
 def history(self,ws):
  key=str(ws.root)
  with self.lock:
   if key not in self.receipts:
    file=ws.resolve('.lumen/workflows/receipts.json',must_exist=False)
    try:rows=json.loads(file.read_text('utf-8')) if file.is_file() and file.stat().st_size<2_000_000 else []
    except (OSError,ValueError):rows=[]
    self.receipts[key]=[r for r in rows[-24:] if isinstance(r,dict)] if isinstance(rows,list) else []
    for row in self.receipts[key]:
     if row.get('state')=='running':row['state']='interrupted'
   changed=False
   for row in self.receipts[key]:
    job=self.features.app.runner.jobs.get(row.get('id'))
    if job and job.done and row['state']=='running':row.update(state='cancelled' if job.cancelled else 'passed' if job.code in (0,None) else 'failed',code=job.code,output=job.output[-16000:],finished=time.time());changed=True
   if changed:self.persist(ws)
   return copy.deepcopy(self.receipts[key])
 def evidence(self,ws,body):
  path=body.get('path','');file=ws.resolve(path)
  if language(path) not in KITS:raise ValueError('Selecciona un archivo de código compatible.')
  if file.name.startswith('.env') or file.suffix.lower() in ('.key','.pem'):raise ValueError('Selecciona un archivo de código, no credenciales.')
  content=body.get('content')
  if not isinstance(content,str) or len(content.encode())>128000:raise ValueError('Adjunta un búfer de código de hasta 128 kB.')
  diagnostics=body.get('diagnostics',[])
  if not isinstance(diagnostics,list) or len(diagnostics)>100:raise ValueError('Demasiados diagnósticos.')
  history=[r for r in self.history(ws) if r.get('path')==path][-3:]
  return {'path':path,'sha256':hashlib.sha256(content.encode()).hexdigest(),'content':content,'consulted':[path],
   'diagnostics':[{k:str(d.get(k,''))[:1000] for k in ('message','line','severity')} for d in diagnostics if isinstance(d,dict)],
   'executions':[{'action':r['action'],'state':r['state'],'commands':r['commands'],'output':r.get('output','')[-6000:]} for r in history],
   'instruction':'Distingue evidencia de hipótesis. Propón un plan de cambios y pruebas; no afirmes haber ejecutado órdenes fuera de este recibo.'}
