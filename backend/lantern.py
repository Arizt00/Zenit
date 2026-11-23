"""Live buffer execution with syntax gating, revision ownership and cooperative checkpoints."""
from __future__ import annotations
import copy
import difflib
import hashlib
import json
import sys
import struct
import shutil
import tempfile
import os
import stat
from .terminals import child_environment
from .lantern_adapters import stage, prepare, runtime_commands, Superseded, buffer_sources
from .diagnostics import marker
from pathlib import Path
from .preferences import atomic_json
from .checkpoint_io import read_checkpoint
import threading
import time
from functools import wraps
from .diagnostics import output_diagnostics

LIVE_DEFAULTS={'inputEnabled':False,'stdin':'','closeInput':True,'verifyEnabled':False,'expectedExit':0,'match':'contains','expectedOutput':'','timeout':0}

def input_fingerprint(options):
    value=[options['inputEnabled'],options['stdin'] if options['inputEnabled'] else '',options['closeInput'] if options['inputEnabled'] else False]
    return hashlib.sha256(json.dumps(value,ensure_ascii=False).encode()).hexdigest()

def baseline_result(job):
    baseline=getattr(job,'lantern_baseline',None)
    if not baseline:return {'status':'off'}
    if not job.done:return {'status':'pending','revision':baseline['revision']}
    if input_fingerprint(job.lantern_options)!=baseline['inputSha256']:return {'status':'differentInput','revision':baseline['revision']}
    complete=job.stream_complete and not job.cancelled and job.command_index==len(job.commands)-1
    return {'status':'passed' if complete and job.code==baseline['code'] and job.stream_sha256==baseline['outputSha256'] else 'failed','revision':baseline['revision']}

def verify_run(job):
    opts=getattr(job,'lantern_options',LIVE_DEFAULTS)
    if not opts['verifyEnabled']:return {'status':'off','checks':[]}
    if not job.done:return {'status':'pending','checks':[]}
    output=job.stream_output.replace('\r\n','\n');expected=opts['expectedOutput'].replace('\r\n','\n')
    checks=[{'name':'Código de salida','passed':not job.cancelled and job.code==opts['expectedExit'],'expected':str(opts['expectedExit']),'actual':str(job.code)}]
    if expected:checks.append({'name':'Salida '+('exacta' if opts['match']=='exact' else 'incluida'),'passed':output==expected if opts['match']=='exact' else expected in output})
    return {'status':'passed' if all(c['passed'] for c in checks) else 'failed','checks':checks}

def serialized_control(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.control_lock:return method(self,*args,**kwargs)
    return call

class Lantern:
    def __init__(self,runtimes,runner,preview):
        self.runtimes=runtimes;self.runner=runner;self.preview=preview
        self.lock=threading.RLock();self.control_lock=threading.RLock();self.event=threading.Event();self.thread=None;self.job=None
        self.memory_dir=None;self.history=[];self.validation=None;self.generation=0;self.content=None;self.version=None;self.shadow=None;self.live_root=None
        self.workspace=None;self.revision=0;self.pending=0;self.stamp=None;self.buffers=[]
        self.checkpoint_cache={}
        self.state={'active':False,'status':'idle','path':'','revision':0,'output':'','diagnostics':[],'preview':None}
        self.options=dict(LIVE_DEFAULTS)

    def options_file(self,workspace,path):
        workspace.resolve(path,must_exist=False)
        return workspace.private_dir('lantern')/hashlib.sha256(path.encode()).hexdigest()[:24]/'options.json'

    def get_options(self,workspace,path):
        file=self.options_file(workspace,path)
        try:
            value=json.loads(file.read_text('utf-8')) if file.is_file() and file.stat().st_size<100000 else {}
            return {**LIVE_DEFAULTS,**self.validate_options(value)}
        except (OSError,ValueError,TypeError):return dict(LIVE_DEFAULTS)

    @staticmethod
    def validate_options(value):
        if not isinstance(value,dict) or set(value)-set(LIVE_DEFAULTS):raise ValueError('Opciones Lantern no válidas.')
        value={**LIVE_DEFAULTS,**value}
        if any(type(value[k]) is not bool for k in ('inputEnabled','closeInput','verifyEnabled')):raise ValueError('Activa las opciones con valores booleanos.')
        if any(not isinstance(value[k],str) or len(value[k].encode())>16384 for k in ('stdin','expectedOutput')):raise ValueError('La entrada y la salida esperada admiten hasta 16 KiB.')
        if value['match'] not in ('contains','exact') or type(value['expectedExit']) is not int or not -255<=value['expectedExit']<=255:raise ValueError('Regla de verificación no válida.')
        if type(value['timeout']) not in (int,float) or not 0<=value['timeout']<=120:raise ValueError('El límite debe estar entre 0 y 120 segundos; 0 no impone límite.')
        return value

    @serialized_control
    def configure(self,workspace,body):
        if not workspace.trusted:raise PermissionError('Autoriza el proyecto para configurar Lantern.')
        path=body.get('path','');options=self.validate_options(body.get('options',{}));file=self.options_file(workspace,path)
        file.parent.mkdir(parents=True,exist_ok=True);atomic_json(file,options)
        with self.lock:
            if self.workspace is workspace and self.state.get('path')==path:self.options=options
        return {'path':path,'options':options,'requiresRestart':self.state.get('active',False)}

    def snapshot(self):
        with self.lock:
            state=copy.deepcopy(self.state)
            state['options']=copy.deepcopy(self.options);state['verification']={'status':'off','checks':[]};state['baselineVerification']={'status':'off'}
            if self.job and state.get("executedGeneration")==self.generation:
                with self.job.lock:
                    state['output']=self.job.output;state['job']=self.job.id;state['code']=self.job.code if self.job.done else None
                    if self.job.done:
                        self.remember(self.job)
                        state['status']='error' if self.job.code else 'watching'
                        state['diagnostics']=output_diagnostics(self.job.output,state['path'])
                    state['verification']=verify_run(self.job)
                    state['baselineVerification']=baseline_result(self.job)
            state['lens']=[]
            if state.get('active') and state.get('executedGeneration')==self.generation and self.memory_dir:
                try:
                    lens=self.memory_dir/'lens.json'
                    if lens.stat().st_size<=256000:
                        data=self.read_json(lens,256000)
                        if data.get('generation')==str(self.generation):state['lens']=data.get('values',[])[:200]
                except (OSError,ValueError,TypeError):pass
            state['history']=copy.deepcopy(self.history[-20:])
            state['memoryMode']='Checkpoint cooperativo'
            state['memoryHelp']='Python: lantern_state · JS/TS: lanternState · C/C++: lantern.h / lantern.hpp · nC: estado JSON con esquema y migración.'
            if self.memory_dir:
                state['checkpoint']=str(self.memory_dir/'state.json')
                try: state['memory']=self.read_json(self.memory_dir/'state.json',1_000_000)
                except (OSError,ValueError): state['memory']={}
                native=self.memory_dir/'state.json.native'
                try:
                    raw=read_checkpoint(native,1_048_608)
                    magic,schema,size,checksum=struct.unpack('<QQQQ',raw[:32])
                    if magic==0x4c554d454e4c4e31 and len(raw)==32+size:
                        state['nativeMemory']={'schema':schema,'bytes':size,'checksum':f'{checksum:016x}','path':str(native)}
                except (OSError,ValueError,struct.error):pass
            return state

    def read_json(self,path,limit):
        # Multiple windows poll the same state; parse each atomic checkpoint once.
        metadata=path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or getattr(metadata,'st_file_attributes',0)&0x400:raise ValueError('Checkpoint no regular.')
        if metadata.st_size>limit:raise ValueError('Checkpoint demasiado grande.')
        key=(metadata.st_mtime_ns,metadata.st_ctime_ns,metadata.st_size,metadata.st_ino)
        cached=self.checkpoint_cache.get(str(path))
        if cached and cached[0]==key:return copy.deepcopy(cached[1])
        data=json.loads(read_checkpoint(path,limit))
        self.checkpoint_cache[str(path)]=(key,data)
        while len(self.checkpoint_cache)>4:self.checkpoint_cache.pop(next(iter(self.checkpoint_cache)))
        return copy.deepcopy(data)

    def template(self,lang):
        suffix={'c':'c','cpp':'cpp','nc':'n'}.get(lang)
        if not suffix:raise ValueError('El soporte nativo está disponible para C, C++ y nC.')
        root=Path(__file__).resolve().parents[1]
        return {'name':'lantern-example.'+suffix,'content':(root/f'examples/lantern/counter.{suffix}').read_text(encoding='utf-8'),'guide':(root/'debugger-support/lantern/README.md').read_text(encoding='utf-8')}

    def settle(self,job):
        if not job or job.done:return
        # The program cooperates at its next safe point; it must checkpoint then exit.
        if self.memory_dir:(self.memory_dir/'state.json.reload').write_text('checkpoint-and-exit',encoding='ascii')
        deadline=time.monotonic()+2
        while not job.done and time.monotonic()<deadline:time.sleep(.025)
        if not job.done:job.cancel()
        deadline=time.monotonic()+3
        while not job.done and time.monotonic()<deadline:time.sleep(.025)
        if not job.done:raise ValueError('El proceso anterior no se ha detenido; se ha evitado ejecutar dos revisiones a la vez.')

    @serialized_control
    def start(self,workspace,path,content=None,version=None,buffers=None):
        if not workspace.trusted:raise PermissionError('Autoriza el proyecto antes de iniciar Lantern.')
        workspace.resolve(path,must_exist=content is None)
        if content is not None and (not isinstance(content,str) or len(content.encode("utf-8"))>2*1024*1024):raise ValueError("Buffer no válido o mayor de 2 MiB.")
        sources=buffer_sources(workspace,path,content if content is not None else workspace.read(path)['content'],buffers)
        active=workspace.resolve(path,must_exist=False).relative_to(workspace.root).as_posix()
        pending=[{'path':name,'content':text} for name,text in sorted(sources.items()) if name!=active]
        self.stop()
        with self.lock:
            key=hashlib.sha256(path.encode()).hexdigest()[:24]
            self.memory_dir=workspace.private_dir('lantern')/key;self.memory_dir.mkdir(parents=True,exist_ok=True)
            try:self.history=json.loads((self.memory_dir/'history.json').read_text(encoding='utf-8'))[-20:]
            except (OSError,ValueError):self.history=[]
            self.revision=max([h.get('revision',0) for h in self.history]+[0])
            self.workspace=workspace;self.event=threading.Event();self.pending=time.monotonic()+.15
            self.options=self.get_options(workspace,path)
            self.content=content;self.version=version;self.generation+=1;self.buffers=pending
            self.state={'active':True,'status':'preparing','path':path,'revision':self.revision,'output':'Preparando Lantern…\n','diagnostics':[],'preview':None,'bufferVersion':version,'bufferMode':content is not None,'generation':self.generation,'lens':[]}
            self.stamp=self.signature()
            self.thread=threading.Thread(target=self.watch,args=(self.event,),daemon=True);self.thread.start()
        return self.snapshot()

    def signature(self):
        try:
            p=self.workspace.resolve(self.state['path']);s=p.stat();return(s.st_mtime_ns,s.st_size)
        except (OSError,ValueError,KeyError,PermissionError):return None

    def buffer(self,workspace,path,content,version=None,buffers=None):
        if not isinstance(content,str) or len(content.encode('utf-8'))>2*1024*1024:raise ValueError('Buffer no válido o mayor de 2 MiB.')
        with self.lock:
            if not self.state['active'] or workspace is not self.workspace or path!=self.state['path']:
                return {'ignored':True}
            sources=buffer_sources(workspace,path,content,buffers)
            active=workspace.resolve(path,must_exist=False).relative_to(workspace.root).as_posix()
            pending=[{'path':name,'content':text} for name,text in sorted(sources.items()) if name!=active]
            if content==self.content and version==self.version and pending==self.buffers:return self.snapshot()
            self.buffers=pending
            self.content=content;self.version=version;self.generation+=1;self.pending=time.monotonic()+.65
            self.state.update(status='debouncing',bufferVersion=version,bufferMode=True,generation=self.generation,diagnostics=[],lens=[],preview=None,job=None)
            validation=self.validation
        if validation and not validation.done:validation.cancel()
        return self.snapshot()

    def saved(self,workspace,path):
        with self.lock:
            if self.content is None and self.state['active'] and workspace is self.workspace and path==self.state['path']:
                self.pending=time.monotonic()+.55
                self.stamp=self.signature()

    @serialized_control
    def restart(self):
        with self.lock:
            if not self.state['active']:raise ValueError('Inicia una sesión Lantern primero.')
            self.generation+=1;self.pending=time.monotonic();self.state["generation"]=self.generation
        return self.snapshot()

    def watch(self,event):
        while not event.wait(.08):
            with self.lock:
                if self.content is None:
                    stamp=self.signature()
                    if stamp!=self.stamp:
                        self.stamp=stamp;self.pending=time.monotonic()+.55;self.generation+=1
                if not self.pending or time.monotonic()<self.pending:continue
                self.pending=0;old=self.job;self.job=None;generation=self.generation
                self.state.update(status='preparing',output='Validando el buffer…\n',diagnostics=[],lens=[],error='',job=None)
                workspace=self.workspace;path=self.state['path'];content=self.content;options=copy.deepcopy(self.options);buffers=self.buffers
            obsolete=lambda:event.is_set() or generation!=self.generation
            try:
                self.settle(old)
                if old:
                    with self.lock:self.remember(old)
                if obsolete():continue
                if content is None:content=workspace.read(path)['content']
                # Reuse no mutable links. All compiler intermediates live in this copy.
                self.preview.stop();self.cleanup_live()
                self.live_root=Path(tempfile.mkdtemp(prefix='ll-'))
                shadow=stage(workspace,path,content,self.live_root,obsolete,buffers)
                from .execution_evidence import context,runtime_signature
                evidence=context(shadow,path,content,obsolete)
                if obsolete():continue
                runtime_stamp=runtime_signature(self.runtimes)
                destination=self.runtimes.execution.selected(workspace) if getattr(self.runtimes,'execution',None) else {'id':'local','kind':'local','label':'Este equipo'}
                runtime_destination={k:destination[k] for k in ('id','kind','label')}
                runtime_environment=getattr(workspace,'environment_path',None)
                plan=prepare(self.runtimes,shadow,path)
                if obsolete():continue
                if plan['checks']:
                    result=self.runner.start(plan['checks'],shadow.root,timeout=90,stop_on_output_limit=False)
                    check=self.runner.jobs[result['job']]
                    with self.lock:self.validation=check
                    while not check.done:
                        if obsolete():
                            check.cancel()
                            deadline=time.monotonic()+3
                            while not check.done and time.monotonic()<deadline:time.sleep(.025)
                            if not check.done:raise ValueError('La validación anterior sigue deteniéndose.')
                            raise Superseded()
                        event.wait(.03)
                    with self.lock:self.validation=None
                    if obsolete():continue
                    if check.code:
                        diagnostics=output_diagnostics(check.output,path)
                        with self.lock:
                            self.state.update(status='waiting' if self.content is not None else 'error',output=check.output,
                                diagnostics=diagnostics,error=diagnostics[0]['message'] if diagnostics else 'La compilación no terminó correctamente. Abre el monitor para ver la salida del compilador.',adapter=plan['adapter'])
                        continue
                with self.lock:
                    if obsolete():continue
                    self.revision+=1;self.shadow=shadow
                    self.state.update(revision=self.revision,status='running',updatedAt=time.time(),executedGeneration=generation,
                        generation=generation,bufferVersion=self.version,adapter=plan['adapter'],lensMode=plan['lensMode'],output='',preview=None)
                    if plan.get('preview'):
                        self.state.update(preview=self.preview.start(shadow,path),status='watching',output='Vista previa del buffer actualizada. El archivo original no se ha guardado.\n')
                    else:
                        checkpoint=self.memory_dir/'state.json';lens=self.memory_dir/'lens.json'
                        (self.memory_dir/'state.json.reload').unlink(missing_ok=True);lens.unlink(missing_ok=True)
                        commands=runtime_commands(plan,checkpoint,lens)
                        runtime_path=os.pathsep.join(dict.fromkeys(str(Path(cmd[0]).parent) for cmd in plan['checks']))
                        result=self.runner.start(commands,shadow.root,timeout=options['timeout'],stdin=options['stdin'] if options['inputEnabled'] else None,close_stdin=options['inputEnabled'] and options['closeInput'],env={'PATH':runtime_path+os.pathsep+child_environment().get('PATH',''),'LUMEN_LANTERN_STATE':str(checkpoint),
                            'LUMEN_LANTERN_REVISION':str(self.revision),'LUMEN_LANTERN_LENS':str(lens),'LUMEN_LANTERN_GENERATION':str(generation)})
                        self.job=self.runner.jobs[result['job']]
                        self.job.lantern_options=options
                        self.job.lantern_baseline=self.get_baseline(workspace,path)
                        self.job.lantern_revision=self.revision
                        self.job.lantern_source_sha256=hashlib.sha256(content.encode()).hexdigest()
                        self.job.lantern_replay_source=content if len(content.encode('utf-8'))<=128000 else None
                        self.job.lantern_context=evidence
                        self.job.lantern_destination=runtime_destination
                        self.job.lantern_environment=runtime_environment
                        self.job.lantern_commands=[*plan['checks'],*commands]
                        self.job.lantern_runtime_sha256=runtime_stamp
            except Superseded:continue
            except Exception as exc:
                with self.lock:
                    if not obsolete():
                        diagnostics=[marker(exc.msg,exc.lineno,exc.offset,source='Lantern')] if isinstance(exc,SyntaxError) else []
                        self.state.update(status='waiting' if isinstance(exc,SyntaxError) and self.content is not None else 'error',error=str(exc),output=str(exc)+'\n',diagnostics=diagnostics)

    def cleanup_live(self):
        path=self.live_root
        if path and path.exists() and path.resolve().parent==Path(tempfile.gettempdir()).resolve() and path.name.startswith('ll-'):
            # Only the private directory allocated by this session is removed.
            for attempt in range(8):
                try:shutil.rmtree(path);break
                except OSError:
                    if attempt==7:raise
                    time.sleep(.1)
        self.live_root=None

    def remember(self,job):
        if not self.memory_dir:return
        stamp=(job.id,baseline_result(job))
        if not job.done or getattr(self,'remembered_job',None)==stamp:return
        source=getattr(job,'lantern_replay_source',None);revision=getattr(job,'lantern_revision',self.state['revision'])
        if source is not None and not (self.memory_dir/f'replay-{revision}.json').exists():
            atomic_json(self.memory_dir/f'replay-{revision}.json',{'source':source,'sourceSha256':hashlib.sha256(source.encode()).hexdigest()})
        entry={'revision':getattr(job,'lantern_revision',self.state['revision']),'path':self.state['path'],'time':time.time(),'code':job.code,'output':job.output[-8000:],'verification':verify_run(job),'elapsedMs':round(job.elapsed*1000),
            'rawOutput':job.stream_output[-4000:],'outputSha256':job.stream_sha256,'outputBytes':job.stream_bytes,'outputComplete':job.stream_complete and job.command_index==len(job.commands)-1,'cancelled':job.cancelled,'sourceSha256':getattr(job,'lantern_source_sha256',''),'baselineVerification':baseline_result(job),
            'context':getattr(job,'lantern_context',None),'target':getattr(job,'lantern_destination',None),'environment':getattr(job,'lantern_environment',None),'commands':getattr(job,'lantern_commands',[]),'runtimeSha256':getattr(job,'lantern_runtime_sha256',None),'replayAvailable':source is not None}
        self.history=[h for h in self.history if h['revision']!=entry['revision']]+[entry]
        self.history=self.history[-20:];atomic_json(self.memory_dir/'history.json',self.history)
        retained={f"replay-{row['revision']}.json" for row in self.history}
        for old in self.memory_dir.glob('replay-*.json'):
            if old.name not in retained and not old.is_symlink():old.unlink(missing_ok=True)
        self.remembered_job=stamp

    def baseline_file(self,workspace,path):
        return self.options_file(workspace,path).with_name('baseline.json')

    def get_baseline(self,workspace,path):
        if not workspace.trusted:raise PermissionError('Autoriza el proyecto para leer su referencia.')
        file=self.baseline_file(workspace,path)
        if not file.is_file():return None
        value=self.read_json(file,8000)
        if not isinstance(value,dict) or not all(k in value for k in ('revision','code','inputSha256','outputSha256')):raise ValueError('La referencia de Lantern no es válida.')
        return value

    @serialized_control
    def set_baseline(self,workspace,body):
        if not workspace.trusted:raise PermissionError('Autoriza el proyecto para cambiar su referencia.')
        path=body.get('path','');file=self.baseline_file(workspace,path)
        with self.lock:
            if body.get('clear') is True:
                file.unlink(missing_ok=True)
                if self.workspace is workspace and self.state.get('path')==path and self.job:self.job.lantern_baseline=None
                return {'baseline':None}
            job=self.job
            if self.workspace is not workspace or self.state.get('path')!=path or not job or not job.done or self.state.get('executedGeneration')!=self.generation:raise ValueError('Completa una ejecución del búfer actual antes de fijar su referencia.')
            if job.cancelled or not job.stream_complete or job.command_index!=len(job.commands)-1:raise ValueError('Una ejecución cancelada o incompleta no puede ser la referencia.')
            value={'revision':job.lantern_revision,'code':job.code,'outputSha256':job.stream_sha256,'outputBytes':job.stream_bytes,'inputSha256':input_fingerprint(job.lantern_options),'sourceSha256':job.lantern_source_sha256,'time':time.time()}
            file.parent.mkdir(parents=True,exist_ok=True);atomic_json(file,value);job.lantern_baseline=value
            return {'baseline':value}

    @serialized_control
    def compare(self,workspace,body):
        with self.lock:
            if workspace is not self.workspace:raise ValueError('Inicia Lantern en este proyecto para consultar sus revisiones.')
            if self.job and self.job.done:self.remember(self.job)
            rows=copy.deepcopy(self.history[-20:])
        if len(rows)<2:raise ValueError('Completa al menos dos revisiones de Lantern antes de compararlas.')
        first=body.get('before',rows[-2]['revision']);second=body.get('after',rows[-1]['revision'])
        try:a=next(r for r in rows if r['revision']==first);b=next(r for r in rows if r['revision']==second)
        except StopIteration:raise ValueError('La revisión ya no está en el historial.')
        if first==second:raise ValueError('Elige dos revisiones distintas.')
        complete=all(r.get('outputComplete') and r.get('outputSha256') and not r.get('cancelled') for r in (a,b))
        return {'path':self.state['path'],'before':a,'after':b,'available':[r['revision'] for r in rows],
            'equivalent':a['code']==b['code'] and a.get('outputSha256')==b.get('outputSha256') if complete else None,
            'diff':'\n'.join(difflib.unified_diff(a.get('rawOutput',a['output']).splitlines(),b.get('rawOutput',b['output']).splitlines(),fromfile=f"Revisión {first}",tofile=f"Revisión {second}",n=2))[:10000],
            'notice':'La comparación usa las huellas de toda la salida capturada; la vista muestra sus últimos 4 000 caracteres. No se ha iniciado otra ejecución.'}

    @serialized_control
    def stop(self):
        with self.lock:
            self.event.set();thread=self.thread;job=self.job;validation=self.validation;self.state['active']=False;self.state['lens']=[]
        if validation and not validation.done:validation.cancel()
        self.settle(job)
        if thread and thread is not threading.current_thread():thread.join(timeout=6)
        with self.lock:
            if thread and thread.is_alive():raise ValueError('Lantern aún está deteniendo su proceso. Inténtalo de nuevo.')
            if job:self.state['output']=job.output;self.remember(job)
            if self.state.get('preview'):self.preview.stop();self.state['preview']=None
            self.cleanup_live()
            self.job=None;self.validation=None;self.thread=None;self.state['status']='stopped';self.pending=0
        return self.snapshot()
