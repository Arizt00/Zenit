"""Native project dependencies, resolved by Conan or the nC package manager."""
import json
import os
from pathlib import Path
import re
import threading
import time
from .foundation import bundled_tool, tool_environment
from .preferences import atomic_json
from .runtime_paths import find_tool

NATIVE_LANGUAGES=('c','cpp','asm')

def native_state(ws):
    ws=getattr(ws,'python_workspace',ws)
    path=ws.resolve('.lumen/dependencies/active.json',must_exist=False)
    if not path.is_file():return {'requires':[],'compile':[],'link':[],'packages':[]}
    data=json.loads(path.read_text(encoding='utf-8'))
    for key in ['compile','link']+[k for k in ('cCompile','cppCompile') if k in data]:
        if not isinstance(data.get(key),list) or any(not isinstance(x,str) or '\0' in x or len(x)>8192 for x in data[key]):raise ValueError('Invalid native dependency flags. Resolve dependencies again.')
    return data

def dependency_finished(features,ws,task,languages):
    """Publish only completed installations, including when the page has been closed."""
    def watch():
        job=features.app.runner.jobs[task['job']]
        while not job.done:time.sleep(.1)
        if job.code not in (0,None) or job.cancelled:return
        if features.app.workspace.root!=ws.root or not ws.trusted:return
        runtime=features.extension_runtime
        for key,host in list(runtime.hosts.items()):
            root=getattr(host,'root',getattr(getattr(host,'workspace',None),'root',None))
            providers=host.capabilities.get('providers',[])
            if root==ws.root and host.process.poll() is None and any(p.get('language') in languages for p in providers):
                try:runtime.start(ws,key,True)
                except Exception as error:runtime.errors[key]='Dependency refresh: '+str(error)[:300]
        features.extension_services.emit('zenit.dependencies.changed',workspace=str(ws.root),languages=list(languages),job=job.id)
    threading.Thread(target=watch,daemon=True).start()

class NativePackages:
    def __init__(self,features):self.features=features;self.jobs={};self.lock=threading.RLock()
    def status(self,ws):
        data=native_state(ws)
        manifest=ws.resolve('ncc.package.json',must_exist=False)
        nc=json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else None
        job=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
        names=('gcc','g++','clangd','as','nasm','gdb','cmake','ninja','ncc')
        return {'native':data,'nc':nc,'tools':[{'id':n,'path':find_tool(n,self.features.runtimes.config.get('tools')),'bundled':bool(bundled_tool(n))} for n in names],
                'task':{'id':job.id,'done':job.done,'code':job.code,'output':job.output[-24000:]} if job else None}
    def start(self,ws,body):
        if not ws.trusted:raise PermissionError('Trust this project before managing dependencies.')
        lang=body.get('language','cpp');action=body.get('action');value=body.get('requirement','')
        if lang not in (*NATIVE_LANGUAGES,'nc'):raise ValueError('Choose C, C++, nC or ASM.')
        if action not in ('install','remove','resolve','check','init'):raise ValueError('Unknown dependency action.')
        with self.lock:
            old=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
            if old and not old.done:raise ValueError('A native dependency task is already running.')
            commands=[];env=tool_environment()
            if lang=='nc':
                ncc=find_tool('ncc',self.features.runtimes.config.get('tools'))
                if not ncc:raise ValueError('The nC compiler is unavailable.')
                manifest=ws.resolve('ncc.package.json',must_exist=False)
                if action=='init':
                    if manifest.exists() or ws.resolve('src/main.n',must_exist=False).exists():raise ValueError('An nC manifest or entry file already exists. It has been preserved.')
                    commands=[[ncc,'package','init',re.sub(r'[^A-Za-z0-9_]','_',ws.root.name) or 'application','--path',str(ws.root)]]
                else:
                    if not manifest.exists():raise ValueError('Prepare the nC package first.')
                    if action in ('install','remove'):
                        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*',value):raise ValueError('Enter a native nC module name, for example stoud::io.')
                        commands.append([ncc,'package','add' if action=='install' else 'remove',value,'--path',str(ws.root)])
                    commands.extend([[ncc,'package','lock','--path',str(ws.root)],[ncc,'package','verify-lock','--path',str(ws.root)]])
                    if action=='check':commands.append([ncc,'package','check','--path',str(ws.root)])
            else:
                if action=='init':raise ValueError('Install a library to prepare native dependencies.')
                python=bundled_tool('python')
                if not python:raise ValueError('The bundled dependency manager is unavailable.')
                requires=list(native_state(ws).get('requires',[]))
                if action=='install':
                    if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.+-]{0,99}/[a-zA-Z0-9_][a-zA-Z0-9_.+-]{0,99}',value):raise ValueError('Enter a Conan reference with a version, for example zlib/1.3.1 or fmt/11.2.0.')
                    requires=[x for x in requires if x.split('/')[0]!=value.split('/')[0]]+[value]
                elif action=='remove':
                    if value not in requires:raise ValueError('This library is not a project dependency.')
                    requires.remove(value)
                folder=ws.private_dir('dependencies');candidate=folder/'request.json'
                tools={k:find_tool(k,self.features.runtimes.config.get('tools')) for k in ('gcc','g++','cmake','ninja')}
                if not all(tools.values()):raise ValueError('GCC, G++, CMake and Ninja are required for native dependencies.')
                atomic_json(candidate,{'workspace':str(ws.root),'requires':requires,'tools':tools})
                worker=Path(__file__).with_name('native_package_worker.py')
                commands=[[python,'-I',str(worker),str(candidate)]]
            task=self.features.app.runner.start(commands,ws.root,timeout=1800,env=env,stop_on_output_limit=False)
            self.jobs[str(ws.root)]=task['job'];dependency_finished(self.features,ws,task,(lang,) if lang=='nc' else NATIVE_LANGUAGES)
            return task
    def cancel(self,ws):
        if not ws.trusted:raise PermissionError('Trust this project before cancelling its task.')
        job=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
        if job and not job.done:job.cancel()
        return {'cancelled':True}
