"""Check modular nC buffers with NCC, including pending dependency buffers."""
import hashlib,json,tempfile,threading,time,uuid
from pathlib import Path
from .lantern_adapters import stage,Superseded
from .nc_project_bridge import materialize_modules,imports
from .terminals import child_environment
from .windows_toolchain import native_environment

LOCK=threading.RLock()
ACTIVE={}
CACHE={}
GATE=threading.BoundedSemaphore(2)

def check(platform,ws,document):
    path=ws.resolve(document.get('path')).relative_to(ws.root).as_posix();text=document.get('text')
    if Path(path).suffix.lower() not in ('.n','.nc') or not isinstance(text,str):raise ValueError('Documento nC no válido.')
    compiler=document.get('compiler') or platform.runtimes.executable('ncc')
    if not isinstance(compiler,str) or not Path(compiler).is_file():raise ValueError('No se encuentra el compilador nC seleccionado.')
    key=(str(ws.root),path);identity=uuid.uuid4().hex
    pending={d['path']:d['content'] for d in (platform.workbenches.snapshot(ws).get('session') or {}).get('documents',[])
             if d.get('dirty') and isinstance(d.get('content'),str) and not Path(d['path']).is_absolute()}
    pending.update({d['path']:d['text'] for d in platform.buffers.snapshot()['buffers'] if not Path(d['path']).is_absolute()})
    pending.pop(path,None)
    buffers=[{'path':p,'content':value} for p,value in pending.items() if Path(p).suffix.lower() in ('.n','.nc')]
    files=[(p,ws.resolve(p).stat().st_mtime_ns,ws.resolve(p).stat().st_size) for p in ws.files() if Path(p).suffix.lower() in ('.n','.nc')]
    stamp=hashlib.sha256(json.dumps([text,buffers,files,compiler,Path(compiler).stat().st_mtime_ns],sort_keys=True).encode()).hexdigest()
    with LOCK:
        cached=CACHE.get(key)
        if cached and cached[0]==stamp and time.monotonic()-cached[1]<15:return cached[2]
        previous=ACTIVE.get(key)
        if previous and previous[1]:previous[1].cancel()
        ACTIVE[key]=(identity,None)
    def obsolete():
        with LOCK:return ACTIVE.get(key,(None,))[0]!=identity
    job=None;acquired=False
    try:
        deadline=time.monotonic()+10
        while not (acquired:=GATE.acquire(timeout=.05)):
            if obsolete() or time.monotonic()>deadline:raise Superseded()
        with tempfile.TemporaryDirectory(prefix='zenit-nc-diagnostics-',ignore_cleanup_errors=True) as temp:
            folder=Path(temp)/'project';shadow=stage(ws,path,text,folder,obsolete,buffers)
            if imports(text):
                materialize_modules(shadow,folder,path)
                commands=[[compiler,'project','sync',str(folder),'--main',path],[compiler,'project','check',str(folder),'--main',path]]
            else:commands=[[compiler,'check',str(folder/path)]]
            if obsolete():raise Superseded()
            run=platform.app.runner.start(commands,folder,timeout=20,env=native_environment(child_environment()))
            job=platform.app.runner.jobs[run['job']]
            with LOCK:
                if obsolete():job.cancel();raise Superseded()
                ACTIVE[key]=(identity,job)
            while not job.done:
                if obsolete():job.cancel()
                time.sleep(.03)
            if obsolete():raise Superseded()
            result={'code':job.code,'output':job.output[-24000:],'authority':'ncc-project-check'}
            with LOCK:
                CACHE[key]=(stamp,time.monotonic(),result)
                while len(CACHE)>64:CACHE.pop(next(iter(CACHE)))
            return result
    except Superseded:return {'cancelled':True,'code':0,'output':''}
    finally:
        if job and not job.done:job.cancel()
        if acquired:GATE.release()
        with LOCK:
            if ACTIVE.get(key,(None,))[0]==identity:ACTIVE.pop(key,None)
