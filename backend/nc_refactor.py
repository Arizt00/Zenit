"""Reviewed public nC module function renames, checked by NCC in fresh copies."""
import hashlib,json,tempfile,threading,time,uuid
from pathlib import Path
from .execution_evidence import runtime_signature
from .lantern_adapters import stage
from .nc_project_bridge import imports,materialize_modules
from .terminals import child_environment
from .windows_toolchain import native_environment
from .runtime_paths import find_tool

LOCK=threading.RLock()
GATE=threading.BoundedSemaphore(1)

def sha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def position(text,offset):
    start=text.rfind('\n',0,offset)+1
    return {'line':text.count('\n',0,offset),'character':len(text[start:offset].encode('utf-16-le'))//2}

def offset(text,point):
    lines=text.splitlines(keepends=True);line=point.get('line');column=point.get('character')
    if type(line) is not int or type(column) is not int or line<0 or line>=len(lines) or column<0:raise ValueError('Posición nC inválida.')
    if column>len(lines[line].rstrip('\r\n').encode('utf-16-le'))//2:raise ValueError('Columna nC fuera del archivo.')
    prefix=lines[line].encode('utf-16-le')[:column*2]
    try:return sum(map(len,lines[:line]))+len(prefix.decode('utf-16-le'))
    except UnicodeError:raise ValueError('La posición divide un carácter Unicode.')

def sources(platform,ws,document=None,buffers=None):
    if buffers is None:buffers=[]
    pending={d['path']:d['content'] for d in (platform.workbenches.snapshot(ws).get('session') or {}).get('documents',[]) if d.get('dirty') and isinstance(d.get('content'),str)}
    pending.update({d['path']:d['text'] for d in platform.buffers.snapshot()['buffers'] if isinstance(d.get('text'),str)})
    if not isinstance(buffers,list) or len(buffers)>64:raise ValueError('Revisa hasta 64 búferes nC pendientes.')
    for d in [*buffers,*([document] if document else [])]:
        if not isinstance(d,dict) or not isinstance(d.get('text'),str):raise ValueError('Búfer nC inválido.')
        path=ws.resolve(d.get('path'),must_exist=False).relative_to(ws.root).as_posix();pending[path]=d['text']
    names=[name for name in ws.files() if Path(name).suffix.lower() in ('.n','.nc')]
    if len(names)>200:raise ValueError('El renombrado nC admite hasta 200 fuentes por proyecto.')
    result={};total=0
    for name in names:
        file=ws.resolve(name)
        if file.stat().st_size>128000:raise ValueError('Una fuente nC supera 128 kB; divide el proyecto para renombrar.')
        text=pending[name] if name in pending else ws.read(name)['content'];size=len(text.encode('utf-8'));total+=size
        if size>128000:raise ValueError('Un búfer nC supera 128 kB.')
        if total>4*1024**2:raise ValueError('Las fuentes nC superan el presupuesto de 4 MiB.')
        result[name]=text
    return result

def stamp(platform,ws,files,compiler):
    tool=Path(compiler);stat=tool.stat();manifest=ws.root/'ncc.package.json'
    if manifest.is_symlink() or manifest.is_file() and manifest.stat().st_size>128000:raise ValueError('Manifiesto nC inválido o demasiado grande.')
    dependencies={};total=0
    for name in ws.files():
        if Path(name).suffix.lower() not in ('.nb','.nbb','.ncp','.nbo','.nm','.lock') and name!='ncc.lock':continue
        file=ws.resolve(name);total+=file.stat().st_size
        if total>64*1024**2:raise ValueError('Las dependencias nC superan el presupuesto de revisión de 64 MiB.')
        digest=hashlib.sha256()
        with file.open('rb') as stream:
            for block in iter(lambda:stream.read(256000),b''):digest.update(block)
        dependencies[name]=digest.hexdigest()
    return sha(json.dumps({'sources':{p:sha(t) for p,t in files.items()},'dependencies':dependencies,'manifest':sha(manifest.read_text('utf-8-sig')) if manifest.is_file() else None,'compiler':[str(tool),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns],'runtime':runtime_signature(platform.runtimes),'target':platform.execution.selected(ws)},sort_keys=True))

def run(platform,root,commands,cancelled=lambda:False):
    if cancelled():raise ValueError('Refactorización nC cancelada.')
    info=platform.app.runner.start(commands,root,timeout=25,env=native_environment(child_environment()),resource_class='background');job=platform.app.runner.jobs[info['job']]
    while not job.done:
        if cancelled() and not job.cancelled:job.cancel()
        time.sleep(.02)
    if job.code!=0 or job.cancelled:raise ValueError('NCC rechazó la refactorización. No se modificaron archivos.\n'+job.output[-5000:])
    return job.stream_output

def validate(platform,ws,files,compiler,entries,cancelled=lambda:False):
    # Fresh stages keep materialized modules from hiding an edited legacy source.
    with tempfile.TemporaryDirectory(prefix='zenit-nc-rename-',ignore_cleanup_errors=True) as temporary:
        root=Path(temporary)/'project';entry=entries[0]
        shadow=stage(ws,entry,files[entry],root,cancelled,[{'path':p,'content':text} for p,text in files.items() if p!=entry]);commands=[]
        for path in entries:
            if imports(files[path]):
                materialize_modules(shadow,root,path)
                commands.extend([[compiler,'project','sync',str(root),'--main',path],[compiler,'project','check',str(root),'--main',path]])
            else:commands.append([compiler,'check',str(root/path)])
        run(platform,root,commands,cancelled)

def rename(platform,ws,host,body,obsolete=lambda:False):
    document=body.get('document') or {};path=ws.resolve(document.get('path')).relative_to(ws.root).as_posix()
    if Path(path).suffix.lower() not in ('.n','.nc'):return None
    text=document.get('text');point=body.get('position')
    if not isinstance(text,str) or not isinstance(point,dict):raise ValueError('Sitúa el cursor sobre una función nC.')
    offset(text,point)
    files=sources(platform,ws,document,body.get('buffers',[]));new=body.get('newName');cancelled=lambda:obsolete() or host.process.poll() is not None
    if not GATE.acquire(blocking=False):raise ValueError('Ya hay una refactorización nC en comprobación. Espera a que termine.')
    try:
        planner=Path(__file__).resolve().parents[1]/'integrations/nc-language/project-rename.cjs';core=host.extension_root/'src/nc_semantic.js'
        if not core.is_file():return None
        with tempfile.TemporaryDirectory(prefix='zenit-nc-binding-') as temporary:
            request=Path(temporary)/'request.json';request.write_text(json.dumps({'sources':files,'path':path,'position':point,'newName':new}),encoding='utf-8')
            plan=json.loads(run(platform,request.parent,[[find_tool('node'),str(planner),str(core),str(request)]],cancelled))
        if plan is None:return None
        target=plan['target'];old=plan['member'];container=plan['container']
        if old==new:return {'items':[]}
        if platform.execution.selected(ws)['kind']!='local':raise ValueError('El renombrado entre módulos requiere la comprobación NCC local.')
        compiler=platform.runtimes.executable('ncc');before_stamp=stamp(platform,ws,files,compiler)
        with tempfile.TemporaryDirectory(prefix='zenit-nc-declaration-') as temporary:
            source=Path(temporary)/Path(target).name;source.write_text(files[target],encoding='utf-8',newline='')
            ast=json.loads(run(platform,source.parent,[[compiler,'emit-ast',str(source)]],cancelled))
        declarations=[fn for row in ast.get('containers',[]) if row.get('name')==container for section in row.get('sections',[]) for fn in section.get('Fn',[]) if fn.get('name')==old]
        if len(declarations)!=1 or declarations[0].get('visibility')!='Public':return None
        edits={row['path']:row['edits'] for row in plan['changes']};count=plan['references'];after=dict(files)
        for name,rows in edits.items():
            value=files[name];operations=sorted([(offset(value,e['range']['start']),offset(value,e['range']['end']),e['newText']) for e in rows],reverse=True);limit=len(value)
            for start,end,replacement in operations:
                if end>limit or value[start:end]!=old or replacement!=new:raise ValueError('Una edición no coincide con su fuente nC.')
                value=value[:start]+replacement+value[end:];limit=start
            after[name]=value
        entries=[name for name,content in files.items() if imports(content)] or [target]
        if len(entries)>16:raise ValueError('La refactorización nC admite hasta 16 entradas de proyecto.')
        validate(platform,ws,files,compiler,entries,cancelled);validate(platform,ws,after,compiler,entries,cancelled)
        if stamp(platform,ws,sources(platform,ws,document,body.get('buffers',[])),compiler)!=before_stamp:raise ValueError('El proyecto cambió durante la comprobación. Solicita de nuevo el renombrado.')
        identity=uuid.uuid4().hex
        with LOCK:
            plans=platform.__dict__.setdefault('_nc_rename_plans',{});plans[identity]={'workspace':str(ws.root),'created':time.monotonic(),'stamp':before_stamp,'compiler':compiler}
            while len(plans)>16:plans.pop(next(iter(plans)))
        rows=[{'uri':(ws.root/name).as_uri(),'edits':value} for name,value in edits.items()]
        return {'items':[{'changes':rows}],'refactor':{'id':identity,'authority':'NCC AST + project check','files':len(rows),'references':count,'scope':'Funciones públicas de contenedores, referencias de módulo cualificadas y sus usos locales; no renombrado semántico universal.'}}
    finally:GATE.release()

def verify(platform,ws,body):
    with LOCK:plan=platform.__dict__.get('_nc_rename_plans',{}).get(body.get('id'))
    if not plan or plan['workspace']!=str(ws.root) or time.monotonic()-plan['created']>300:raise ValueError('La revisión nC caducó. Solicita de nuevo el renombrado.')
    if stamp(platform,ws,sources(platform,ws,buffers=body.get('buffers',[])),plan['compiler'])!=plan['stamp']:raise ValueError('El proyecto o sus búferes cambiaron después de comprobar el renombrado.')
    return {'valid':True}
