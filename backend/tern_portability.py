"""Reproducible Lantern descriptors and bounded offline resource bundles.

Preparation actions are generated here, never executed from descriptor strings.
"""
from concurrent.futures import CancelledError
import hashlib,json,os,platform,re,shutil,stat,subprocess,time,uuid,zipfile
from pathlib import Path,PurePosixPath
from packaging.utils import canonicalize_name,parse_wheel_filename
from packaging.version import Version
from .preferences import atomic_json
from .terminals import child_environment

LIMIT=8*1024**3
INVENTORY="""import sys,platform,json,importlib.metadata as m
items={}
for d in m.distributions():
 n=d.metadata.get('Name');v=d.version
 if n and v:items[n.lower()]={'name':n,'version':v,'editable':bool(json.loads(d.read_text('direct_url.json') or '{}').get('dir_info',{}).get('editable'))}
print(json.dumps({'version':platform.python_version(),'implementation':platform.python_implementation(),'system':platform.system(),'machine':platform.machine(),'dependencies':list(items.values())}))
"""

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

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
    def wheels(self,folder,data):
        wanted={(canonicalize_name(x['name']),Version(x['version'])) for x in data['dependencies']};found={}
        for wheel in sorted(folder.glob('*.whl')):
            if wheel.is_symlink() or getattr(wheel.lstat(),'st_file_attributes',0)&0x400:continue
            try:name,version,_,_=parse_wheel_filename(wheel.name)
            except ValueError:continue
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
            folder=self.resource_folder(directory,'wheels')
            if body.get('download') is True:
                if any(x.get('editable') for x in data['dependencies']):raise ValueError('Convierte las dependencias editables en ruedas antes de exportar.')
                requirements=artifacts/'requirements.txt';requirements.write_text(self.requirements(data),encoding='utf-8')
                self.run(ws,[str(self.tern.python(directory)),'-I','-m','pip','--isolated','download','--only-binary=:all:','--no-deps','--index-url','https://pypi.org/simple','--dest',str(folder),'-r',str(requirements)],event,'Reunir ruedas para exportar')
            available=self.wheels(folder,data)
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
        report={'complete':not missing,'missing':missing,'toolsRequired':data['tools'],'missingToolsHere':self.tool_report(data),'target':data['target'],'note':'El intérprete y QEMU se instalan mediante SDK; el paquete contiene las dependencias y los discos indicados.'}
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
        return {'file':output.name,'report':report}
    def inspect(self,ws,filename):
        path=ws.resolve(filename)
        if not path.name.endswith('.tern.zip'):raise ValueError('Selecciona un paquete .tern.zip del proyecto.')
        with zipfile.ZipFile(path) as bundle:
            infos=bundle.infolist();names=[x.filename for x in infos]
            if len(infos)>4004 or len(names)!=len(set(names)) or sum(x.file_size for x in infos)>LIMIT+2000000:raise ValueError('Paquete de entorno demasiado grande o duplicado.')
            if any(x.flag_bits&1 or stat.S_ISLNK(x.external_attr>>16) or PurePosixPath(x.filename).is_absolute() or '..' in PurePosixPath(x.filename).parts or '\\' in x.filename for x in infos):raise ValueError('Ruta o enlace no permitido en el paquete.')
            if bundle.getinfo('environment.tern').file_size>1000000:raise ValueError('Descriptor demasiado grande.')
            data=self.validate(json.loads(bundle.read('environment.tern')));items=data.get('artifacts')
            if not isinstance(items,list) or len(items)>4000:raise ValueError('Recursos de entorno inválidos.')
            allowed={'environment.tern','report.json'};missing=[]
            for item in items:
                name=item.get('path','');valid=bool(re.fullmatch(r'wheels/[A-Za-z0-9_.+!-]+\.whl',name)) if data['kind']=='python' else name in ('vm/disk.qcow2','vm/seed.iso')
                if not valid or name in allowed or type(item.get('bytes')) is not int or not re.fullmatch('[a-f0-9]{64}',item.get('sha256','')):raise ValueError('Recurso del descriptor inválido.')
                allowed.add(name)
                try:info=bundle.getinfo(name)
                except KeyError:missing.append(name);continue
                if info.file_size!=item['bytes']:raise ValueError('El tamaño de un recurso cambió.')
                digest=hashlib.sha256()
                with bundle.open(name) as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
                if digest.hexdigest()!=item['sha256']:raise ValueError('La huella de un recurso cambió.')
            if set(names)-allowed:raise ValueError('El paquete contiene recursos sin declarar.')
            if data['kind']=='python':
                available=set()
                for item in items:
                    name,version,_,_=parse_wheel_filename(PurePosixPath(item['path']).name);available.add((name,version))
                missing += [x['name']+'=='+x['version'] for x in data['dependencies'] if x.get('editable') or (canonicalize_name(x['name']),Version(x['version'])) not in available]
            else:missing += [name for name in ('vm/disk.qcow2','vm/seed.iso') if name not in allowed]
            tools=self.tool_report(data)
            return {'descriptor':data,'report':{'complete':not missing and not tools,'missing':missing,'missingToolsHere':tools,'toolsRequired':data['tools']}}
    def rebuild(self,ws,body,event):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para reconstruir su entorno.')
        result=self.inspect(ws,body.get('file'));data=result['descriptor']
        if not result['report']['complete']:raise ValueError('Faltan recursos o herramientas: '+', '.join(result['report']['missing']+result['report']['missingToolsHere']))
        if body.get('consent') is not True:raise PermissionError('Revisa y autoriza la reconstrucción del entorno.')
        identity=None
        try:
            if data['kind']=='python':identity=self.tern.create(ws,{'kind':'python','name':data['name'],'inherit':False},event)['environment']
            else:
                with self.tern.lock:
                    if len(self.tern.sessions)>=8:raise ValueError('Cierra un entorno antes de reconstruir otro.')
                identity=uuid.uuid4().hex;directory=self.tern.directory(ws,identity);directory.mkdir(parents=True);atomic_json(directory/'owner.json',{'schema':1,'id':identity,'kind':'arch'})
                self.tern.sessions[identity]=dict(id=identity,name=str(data['name'])[:80],kind='arch',saved=None,state='ready',terminal=None,created=time.time(),workspace=str(ws.root),ws=ws,resources=self.tern.resources(data.get('resources',{})))
            directory,_=self.tern.owned(ws,identity);folder=self.resource_folder(directory)
            with zipfile.ZipFile(ws.resolve(body['file'])) as bundle:
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
                actual={(canonicalize_name(p['name']),p['version']) for p in self.inventory(self.tern.python(directory))['dependencies']}
                if any((canonicalize_name(p['name']),p['version']) not in actual for p in data['dependencies']):raise ValueError('Las versiones reconstruidas no coinciden con el descriptor.')
            elif data['kind']=='arch':self.tern.sessions[identity]['profile']={'id':identity,'name':data['name'],'type':'arch','disk':str(directory/'disk.qcow2'),'seed':str(directory/'seed.iso'),**self.tern.sessions[identity]['resources']}
            if event.is_set():raise CancelledError()
            filename='restored-'+identity[:8]+'.tern';self.tern.save(ws,identity,filename)
            return {'environment':identity,'file':filename,'offline':True}
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
