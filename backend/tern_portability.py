"""Reproducible Lantern descriptors and bounded offline resource bundles.

Preparation actions are generated here, never executed from descriptor strings.
"""
from concurrent.futures import CancelledError
import hashlib,json,os,platform,re,shutil,stat,subprocess,tempfile,time,uuid,zipfile
from pathlib import Path,PurePosixPath
from packaging.utils import canonicalize_name,parse_wheel_filename
from packaging.version import Version
from .preferences import atomic_json
from .terminals import child_environment
from contextlib import nullcontext

LIMIT=8*1024**3
INVENTORY="""import sys,platform,json,importlib.metadata as m
items={}
for d in m.distributions():
 n=d.metadata.get('Name');v=d.version
 if n and v:items[n.lower()]={'name':n,'version':v,'editable':bool(json.loads(d.read_text('direct_url.json') or '{}').get('dir_info',{}).get('editable'))}
try:
 from packaging.tags import sys_tags
except ImportError:
 from pip._vendor.packaging.tags import sys_tags
print(json.dumps({'version':platform.python_version(),'implementation':platform.python_implementation(),'system':platform.system(),'machine':platform.machine(),'dependencies':list(items.values()),'wheelTags':[str(t) for t in sys_tags()]}))
"""

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def environment_id(data):
    """Relocation-independent identity of the lock, tools, platform and resources."""
    lock={k:data.get(k) for k in ('kind','target','platform','tools','dependencies','preparation','resources','artifacts')}
    return hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class TernPortability:
    def __init__(self,tern):self.tern=tern;self.features=tern.features
    def inventory(self,python):
        result=subprocess.run([str(python),'-I','-c',INVENTORY],capture_output=True,env=child_environment(),timeout=30,creationflags=0x08000000 if os.name=='nt' else 0)
        if result.returncode or len(result.stdout)>1000000:raise ValueError('No se pudo inventariar el entorno Python.')
        data=json.loads(result.stdout);self.dependencies(data['dependencies']);return data
    @staticmethod
    def dependencies(items):
        if not isinstance(items,list) or len(items)>2000:raise ValueError('Inventario de dependencias demasiado grande.')
        seen=set()
        for item in items:
            if not isinstance(item,dict) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,150}',str(item.get('name',''))):raise ValueError('Nombre de dependencia inválido.')
            Version(item.get('version',''));key=canonicalize_name(item['name'])
            if key in seen:raise ValueError('Dependencia duplicada.')
            seen.add(key)
        return items
    def describe(self,ws,session):
        directory,_=self.tern.owned(ws,session['id'])
        data={k:session[k] for k in ('id','kind','name','created')}
        data.update(schema=2,type='zenit-environment',target={'kind':'local' if session['kind']=='python' else 'vm'},platform={'system':platform.system(),'machine':platform.machine()},artifacts=[])
        if session['kind']=='python':
            inventory=self.inventory(self.tern.python(directory))
            data.update(inherit=False,sourceInherit=session.get('inherit',True),tools=[{'name':'python','version':inventory['version'],'implementation':inventory['implementation']}],dependencies=sorted(inventory['dependencies'],key=lambda p:p['name'].casefold()),preparation=[{'action':'python.venv'},{'action':'python.install-locked'}])
        else:
            base=self.features.machines.vm_base();version=''
            if base['qemu']:
                result=subprocess.run([base['qemu'],'--version'],capture_output=True,timeout=10,creationflags=0x08000000 if os.name=='nt' else 0)
                version=result.stdout.decode('utf-8','replace').splitlines()[0][:160]
            data.update(resources=session.get('resources',self.tern.resources({})),tools=[{'name':'qemu-system-x86_64','version':version}],dependencies=[],preparation=[{'action':'vm.restore-disk'}])
        return data
    def validate(self,data):
        if not isinstance(data,dict) or data.get('schema')!=2 or data.get('type')!='zenit-environment' or data.get('kind') not in ('python','arch'):raise ValueError('Se necesita un descriptor .tern reproducible de la R17.')
        self.dependencies(data.get('dependencies'))
        if not isinstance(data.get('name'),str) or not 1<=len(data['name'])<=80:raise ValueError('Nombre del entorno inválido.')
        expected=['python.venv','python.install-locked'] if data['kind']=='python' else ['vm.restore-disk']
        if data.get('preparation')!=[{'action':x} for x in expected]:raise ValueError('El descriptor contiene pasos de preparación no admitidos.')
        tools=data.get('tools')
        if not isinstance(tools,list) or len(tools)!=1 or not isinstance(tools[0],dict) or tools[0].get('name')!=('python' if data['kind']=='python' else 'qemu-system-x86_64') or not isinstance(tools[0].get('version'),str) or len(tools[0]['version'])>160:raise ValueError('Herramientas del descriptor inválidas.')
        if data['kind']=='arch':self.tern.resources(data.get('resources',{}))
        return data
    def read(self,ws,filename):
        path=ws.resolve(filename)
        if path.suffix!='.tern' or path.stat().st_size>1000000:raise ValueError('Descriptor .tern inválido.')
        return self.validate(json.loads(path.read_text(encoding='utf-8')))
    def run(self,ws,argv,event,label,timeout=900):
        self.features.hilo.report(event,label)
        task=self.features.app.runner.start([argv],ws.root,timeout=timeout,env={'PIP_DISABLE_PIP_VERSION_CHECK':'1','PYTHONUTF8':'1'})
        job=self.features.app.runner.jobs[task['job']]
        while not job.done:
            if event.wait(.1):job.cancel()
        if event.is_set():raise CancelledError()
        if job.code:raise ValueError(label+' falló. '+job.output[-1800:])
    def wheels(self,folder,data,tags=None):
        wanted={(canonicalize_name(x['name']),Version(x['version'])) for x in data['dependencies']};found={}
        for wheel in sorted(folder.glob('*.whl')):
            if wheel.is_symlink() or getattr(wheel.lstat(),'st_file_attributes',0)&0x400:continue
            try:name,version,_,wheel_tags=parse_wheel_filename(wheel.name)
            except ValueError:continue
            if tags is not None and not tags.intersection(map(str,wheel_tags)):continue
            if (name,version) in wanted:found.setdefault((name,version),[]).append(wheel)
        return found
    def requirements(self,data):return '\n'.join(f"{x['name']}=={x['version']}" for x in data['dependencies'])+'\n'
    def tool_report(self,data):
        missing=[]
        if data['kind']=='python':
            executable=self.features.python_packages.base()
            if not executable:missing.append('Python '+data['tools'][0]['version'])
            else:
                actual=self.inventory(executable)
                if actual['version']!=data['tools'][0]['version'] or actual['implementation']!=data['tools'][0].get('implementation'):missing.append('Python exacto '+data['tools'][0]['version']+' (disponible '+actual['version']+')')
            if data.get('platform')!={'system':platform.system(),'machine':platform.machine()}:missing.append('La plataforma del entorno difiere de este equipo; exporta ruedas compatibles desde su plataforma de destino.')
        else:
            qemu=self.features.machines.vm_base()['qemu']
            if not qemu:missing.append('QEMU x86_64')
            else:
                result=subprocess.run([qemu,'--version'],capture_output=True,timeout=10,creationflags=0x08000000 if os.name=='nt' else 0)
                lines=result.stdout.decode('utf-8','replace').splitlines();actual=lines[0][:160] if lines else ''
                if result.returncode or actual!=data['tools'][0]['version']:missing.append('QEMU exacto '+data['tools'][0]['version']+' (disponible '+(actual or 'desconocido')+')')
        return missing
    def export(self,ws,body,event):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para exportar su entorno.')
        data=self.read(ws,body.get('file'));directory,_=self.tern.owned(ws,data.get('id'));artifacts=self.resource_folder(directory)
        files={};missing=[]
        if data['kind']=='python':
            inventory=self.inventory(self.tern.python(directory))
            expected={(canonicalize_name(p['name']),p['version'],bool(p.get('editable'))) for p in data['dependencies']}
            actual={(canonicalize_name(p['name']),p['version'],bool(p.get('editable'))) for p in inventory['dependencies']}
            if expected!=actual or inventory['version']!=data['tools'][0]['version'] or inventory['implementation']!=data['tools'][0].get('implementation'):raise ValueError('El entorno cambió después de guardar el descriptor. Guarda un .tern nuevo antes de exportarlo.')
            folder=self.resource_folder(directory,'wheels')
            if body.get('download') is True:
                if any(x.get('editable') for x in data['dependencies']):raise ValueError('Convierte las dependencias editables en ruedas antes de exportar.')
                requirements=artifacts/'requirements.txt';requirements.write_text(self.requirements(data),encoding='utf-8')
                self.run(ws,[str(self.tern.python(directory)),'-I','-m','pip','--isolated','download','--only-binary=:all:','--no-deps','--index-url','https://pypi.org/simple','--dest',str(folder),'-r',str(requirements)],event,'Reunir ruedas para exportar')
            available=self.wheels(folder,data,set(inventory['wheelTags']))
            for item in data['dependencies']:
                key=(canonicalize_name(item['name']),Version(item['version']))
                if item.get('editable'):missing.append(item['name']+': dependencia editable, necesita una rueda reproducible')
                elif key not in available:missing.append(item['name']+'=='+item['version']+': falta su rueda')
                else:
                    for wheel in available[key]:files['wheels/'+wheel.name]=wheel
        else:
            if data['id'] in self.features.machines.active:raise ValueError('Detén la máquina virtual antes de exportar su disco.')
            base=self.features.machines.vm_base()
            if not base['qimg']:missing.append('qemu-img para convertir el disco independiente')
            else:
                flat=artifacts/'disk.qcow2'
                if flat.exists():flat.unlink()
                self.run(ws,[base['qimg'],'convert','-f','qcow2','-O','qcow2',str(directory/'disk.qcow2'),str(flat)],event,'Exportar disco sin base externa',timeout=1800)
                files['vm/disk.qcow2']=flat;files['vm/seed.iso']=directory/'seed.iso'
        self.features.hilo.report(event,'Verificar recursos del entorno')
        data['artifacts']=[{'path':name,'bytes':path.stat().st_size,'sha256':sha(path)} for name,path in files.items()]
        if sum(x['bytes'] for x in data['artifacts'])>LIMIT:raise ValueError('La exportación supera 8 GB.')
        report={'complete':not missing,'missing':missing,'toolsRequired':data['tools'],'missingToolsHere':self.tool_report(data),'target':data['target'],'environmentId':environment_id(data),'note':'El intérprete y QEMU se instalan mediante SDK; el paquete contiene las dependencias y los discos indicados.'}
        output=ws.resolve(body['file']+'.zip',must_exist=False)
        # Exclusive creation protects every existing export. Cancellation removes only this new file.
        created=False
        try:
            with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_STORED) as bundle:
                created=True;bundle.writestr('environment.tern',json.dumps(data,ensure_ascii=False,indent=2));bundle.writestr('report.json',json.dumps(report,ensure_ascii=False,indent=2))
                for name,path in files.items():
                    if event.is_set():raise CancelledError()
                    bundle.write(path,name)
            if event.is_set():raise CancelledError()
        except BaseException:
            if created:output.unlink(missing_ok=True)
            raise
        return {'file':output.name,'report':{**report,'bundleSha256':sha(output)}}
    def inspect(self,ws,filename,_source=None,event=None):
        path=ws.resolve(filename)
        if not path.name.endswith('.tern.zip'):raise ValueError('Selecciona un paquete .tern.zip del proyecto.')
        if path.stat().st_size>LIMIT+2000000:raise ValueError('Paquete de entorno demasiado grande.')
        with (path.open('rb') if _source is None else nullcontext(_source)) as source:
            digest=hashlib.sha256()
            for block in iter(lambda:source.read(1024*1024),b''):
                if event and event.is_set():raise CancelledError()
                digest.update(block)
            bundle_hash=digest.hexdigest();source.seek(0)
            return self.inspect_archive(source,bundle_hash,event)
    def inspect_archive(self,source,bundle_hash,event=None):
        with zipfile.ZipFile(source) as bundle:
            infos=bundle.infolist();names=[x.filename for x in infos]
            if len(infos)>4004 or len(names)!=len(set(names)) or sum(x.file_size for x in infos)>LIMIT+2000000:raise ValueError('Paquete de entorno demasiado grande o duplicado.')
            if any(x.flag_bits&1 or stat.S_ISLNK(x.external_attr>>16) or PurePosixPath(x.filename).is_absolute() or '..' in PurePosixPath(x.filename).parts or '\\' in x.filename for x in infos):raise ValueError('Ruta o enlace no permitido en el paquete.')
            if bundle.getinfo('environment.tern').file_size>1000000:raise ValueError('Descriptor demasiado grande.')
            data=self.validate(json.loads(bundle.read('environment.tern')));items=data.get('artifacts')
            if not isinstance(items,list) or len(items)>4000:raise ValueError('Recursos de entorno inválidos.')
            allowed={'environment.tern','report.json'};missing=[]
            for item in items:
                if event and event.is_set():raise CancelledError()
                name=item.get('path','');valid=bool(re.fullmatch(r'wheels/[A-Za-z0-9_.+!-]+\.whl',name)) if data['kind']=='python' else name in ('vm/disk.qcow2','vm/seed.iso')
                if not valid or name in allowed or type(item.get('bytes')) is not int or not re.fullmatch('[a-f0-9]{64}',item.get('sha256','')):raise ValueError('Recurso del descriptor inválido.')
                allowed.add(name)
                try:info=bundle.getinfo(name)
                except KeyError:missing.append(name);continue
                if info.file_size!=item['bytes']:raise ValueError('El tamaño de un recurso cambió.')
                digest=hashlib.sha256()
                with bundle.open(name) as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):
                        if event and event.is_set():raise CancelledError()
                        digest.update(block)
                if digest.hexdigest()!=item['sha256']:raise ValueError('La huella de un recurso cambió.')
            if set(names)-allowed:raise ValueError('El paquete contiene recursos sin declarar.')
            if data['kind']=='python':
                available=set()
                python=self.features.python_packages.base();tags=set(self.inventory(python)['wheelTags']) if python else set()
                for item in items:
                    name,version,_,wheel_tags=parse_wheel_filename(PurePosixPath(item['path']).name)
                    if item['path'] in names and tags.intersection(map(str,wheel_tags)):available.add((name,version))
                    elif item['path'] in names:missing.append(item['path']+': rueda incompatible con el intérprete de destino')
                missing += [x['name']+'=='+x['version'] for x in data['dependencies'] if x.get('editable') or (canonicalize_name(x['name']),Version(x['version'])) not in available]
            else:missing += [name for name in ('vm/disk.qcow2','vm/seed.iso') if name not in allowed]
            tools=self.tool_report(data)
            return {'descriptor':data,'report':{'complete':not missing and not tools,'missing':missing,'missingToolsHere':tools,'toolsRequired':data['tools'],'bundleSha256':bundle_hash,'environmentId':environment_id(data)}}
    def rebuild(self,ws,body,event):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para reconstruir su entorno.')
        if body.get('consent') is not True:raise PermissionError('Revisa y autoriza la reconstrucción del entorno.')
        expected=body.get('bundleSha256')
        if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Comprueba el paquete antes de reconstruirlo; falta la huella revisada.')
        # The exact reviewed bytes are staged before creating an interpreter or
        # executing pip. Replacing the original archive cannot change this job.
        with tempfile.TemporaryFile() as staged:
            path=ws.resolve(body.get('file'))
            if path.stat().st_size>LIMIT+2000000:raise ValueError('Paquete de entorno demasiado grande.')
            digest=hashlib.sha256();total=0
            with path.open('rb') as source:
                for block in iter(lambda:source.read(1024*1024),b''):
                    if event.is_set():raise CancelledError()
                    total+=len(block)
                    if total>LIMIT+2000000:raise ValueError('Paquete de entorno demasiado grande.')
                    digest.update(block);staged.write(block)
            if digest.hexdigest()!=expected:raise ValueError('El paquete cambió desde la revisión. Vuelve a comprobarlo antes de reconstruir.')
            staged.seek(0);result=self.inspect(ws,body['file'],_source=staged,event=event)
            return self.restore_verified(ws,body,event,result,staged)
    def restore_verified(self,ws,body,event,result,staged):
        data=result['descriptor']
        if not result['report']['complete']:raise ValueError('Faltan recursos o herramientas: '+', '.join(result['report']['missing']+result['report']['missingToolsHere']))
        identity=None
        try:
            if data['kind']=='python':identity=self.tern.create(ws,{'kind':'python','name':data['name'],'inherit':False},event)['environment']
            else:
                with self.tern.lock:
                    if len(self.tern.sessions)>=8:raise ValueError('Cierra un entorno antes de reconstruir otro.')
                identity=uuid.uuid4().hex;directory=self.tern.directory(ws,identity);directory.mkdir(parents=True);atomic_json(directory/'owner.json',{'schema':1,'id':identity,'kind':'arch'})
                self.tern.sessions[identity]=dict(id=identity,name=str(data['name'])[:80],kind='arch',saved=None,state='ready',terminal=None,created=time.time(),workspace=str(ws.root),ws=ws,resources=self.tern.resources(data.get('resources',{})))
            directory,_=self.tern.owned(ws,identity);folder=self.resource_folder(directory)
            staged.seek(0)
            with zipfile.ZipFile(staged) as bundle:
                for item in data['artifacts']:
                    if event.is_set():raise CancelledError()
                    target=folder/item['path'] if data['kind']=='python' else directory/PurePosixPath(item['path']).name;target.parent.mkdir(exist_ok=True,parents=True)
                    with bundle.open(item['path']) as source,target.open('xb') as destination:shutil.copyfileobj(source,destination,1024*1024)
                    if sha(target)!=item['sha256']:raise ValueError('El recurso cambió durante la reconstrucción.')
            if data['kind']=='python' and data['dependencies']:
                wheels=self.wheels(folder/'wheels',data);lines=[]
                for package in data['dependencies']:
                    candidates=wheels[(canonicalize_name(package['name']),Version(package['version']))]
                    lines.append(package['name']+'=='+package['version']+' '+' '.join('--hash=sha256:'+sha(p) for p in candidates))
                locked=folder/'requirements.lock';locked.write_text('\n'.join(lines)+'\n',encoding='utf-8')
                self.run(ws,[str(self.tern.python(directory)),'-I','-m','pip','--isolated','install','--no-index','--no-deps','--require-hashes','--find-links',str(folder/'wheels'),'-r',str(locked)],event,'Reconstruir dependencias sin red')
            elif data['kind']=='arch':
                qimg=self.features.machines.vm_base().get('qimg')
                if not qimg:raise ValueError('Falta qemu-img para verificar el disco reconstruido.')
                info=subprocess.run([qimg,'info','-f','qcow2','--output=json',str(directory/'disk.qcow2')],capture_output=True,timeout=20,creationflags=0x08000000 if os.name=='nt' else 0)
                disk=json.loads(info.stdout) if not info.returncode else {}
                if disk.get('format')!='qcow2' or disk.get('backing-filename'):raise ValueError('El disco portátil debe ser qcow2 independiente, sin una base externa.')
                self.tern.sessions[identity]['profile']={'id':identity,'name':data['name'],'type':'arch','disk':str(directory/'disk.qcow2'),'seed':str(directory/'seed.iso'),**self.tern.sessions[identity]['resources']}
            if data['kind']=='python':
                actual={(canonicalize_name(p['name']),p['version']) for p in self.inventory(self.tern.python(directory))['dependencies']}
                if any((canonicalize_name(p['name']),p['version']) not in actual for p in data['dependencies']):raise ValueError('Las versiones reconstruidas no coinciden con el descriptor.')
                self.run(ws,[str(self.tern.python(directory)),'-I','-m','pip','--isolated','check'],event,'Comprobar dependencias reconstruidas')
            if event.is_set():raise CancelledError()
            filename='restored-'+identity[:8]+'.tern'
            receipt={'schema':1,'kind':data['kind'],'environmentId':result['report']['environmentId'],'bundleSha256':result['report']['bundleSha256'],'created':time.time(),'offline':True,'verified':['artifact-sha256','exact-tools','wheel-tags','installed-versions','pip-check'] if data['kind']=='python' else ['artifact-sha256','exact-tools','independent-disk'],'scope':'Reconstrucción local verificada. No acredita un segundo equipo ni el arranque del sistema invitado.'}
            atomic_json(directory/'reconstruction.json',receipt)
            self.tern.save(ws,identity,filename)
            return {'environment':identity,'file':filename,'offline':True,'receipt':receipt}
        except BaseException:
            if identity:
                self.tern.sessions.pop(identity,None);self.tern.remove_owned(ws,identity)
            raise
    @staticmethod
    def resource_folder(directory,child=''):
        folder=directory/'portable'
        for target in ([folder,folder/child] if child else [folder]):
            if target.is_symlink() or target.exists() and getattr(target.lstat(),'st_file_attributes',0)&0x400:raise PermissionError('Los recursos no pueden usar enlaces o uniones.')
            target.mkdir(exist_ok=True)
            for entry in target.iterdir():
                if entry.is_symlink() or getattr(entry.lstat(),'st_file_attributes',0)&0x400:raise PermissionError('Los recursos no pueden contener enlaces o uniones.')
        return folder/child if child else folder
