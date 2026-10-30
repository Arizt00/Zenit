"""Project tests: passive source discovery, reviewed argv and real result files."""
import ast,hashlib,json,re,threading,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
from .foundation import python_command
from .runtime_paths import find_tool
from .preferences import atomic_json
from .change_footprint import SUFFIXES,BUILD_FILES
from .testing_paths import ctest_directories,nc_entries

class ProjectTests:
    def __init__(self,features):self.features=features;self.runs={};self.lock=threading.RLock()
    @staticmethod
    def source_hashes(ws):
        hashes={};budget=8*1024**2
        for name in ws.files():
            file=ws.resolve(name)
            if file.suffix.lower() not in SUFFIXES|{'.toml'} and file.name not in BUILD_FILES:continue
            try:
                if file.stat().st_size>min(1000000,budget):continue
                text=file.read_text(encoding='utf-8-sig').replace('\r\n','\n')
            except (OSError,UnicodeError):continue
            raw=text.encode();budget-=len(raw);hashes[name]=hashlib.sha256(raw).hexdigest()
        return hashes
    def discover(self,ws):
        candidates=[];names=ws.files()
        for name in names:
            path=ws.resolve(name)
            if path.suffix.lower()=='.n' or path.suffix=='.py' and path.name.startswith('test'):
                try:s=path.stat();candidates.append((name,s.st_mtime_ns,s.st_ctime_ns,s.st_size))
                except OSError:pass
        directories=ctest_directories(ws,names)
        markers=[(name,ws.resolve(name,must_exist=False).is_file()) for name in ('Cargo.toml','ncc.package.json')]
        signature=hashlib.sha256(json.dumps([candidates,markers,directories]).encode()).hexdigest()
        return self.features.hilo.cached(('test-discovery',str(ws.root),signature),lambda:self._discover(ws,[row[0] for row in candidates],directories),ttl=60)
    def _discover(self,ws,names,directories=()):
        files=[];frameworks=[{'id':'unittest','label':'Python · unittest'},{'id':'pytest','label':'Python · pytest (requiere el paquete)'}]
        if ws.resolve('Cargo.toml',must_exist=False).is_file():frameworks.append({'id':'cargo','label':'Rust · Cargo'})
        if directories:frameworks.append({'id':'ctest','label':'C / C++ / NASM · CTest'})
        native=nc_entries(ws,names)
        if native:frameworks.append({'id':'ncc','label':'nC · comprobación de humo NCC'})
        for name in names:
            path=ws.resolve(name)
            if path.suffix!='.py' or not path.name.startswith('test'):continue
            try:
                if path.stat().st_size>1000000:continue
                tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            except (OSError,SyntaxError,UnicodeError):continue
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):files.append({'id':name+'::'+node.name,'path':name,'line':node.lineno,'name':node.name,'framework':'pytest'})
                if isinstance(node,ast.ClassDef):
                    unit=any(isinstance(base,ast.Attribute) and base.attr=='TestCase' or isinstance(base,ast.Name) and base.id.endswith('TestCase') for base in node.bases)
                    for member in node.body:
                        if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)) and member.name.startswith('test') and (unit or node.name.startswith('Test')):files.append({'id':name+'::'+node.name+'.'+member.name,'path':name,'line':member.lineno,'name':node.name+'.'+member.name,'framework':'unittest' if unit else 'pytest'})
            if len(files)>5000:raise ValueError('El explorador admite hasta 5000 pruebas por proyecto.')
        return {'tests':files+native,'frameworks':frameworks,'ctestDirectories':list(directories),'discovery':'Python: AST. nC: referencias main. No se importa ni ejecuta código del proyecto.'}
    def failed_selections(self,ws,identity,framework):
        record=self.runs.get(identity)
        if not record or record['workspace']!=str(ws.root) or self.active(record):raise ValueError('Espera a que termine la ejecución de este proyecto.')
        if framework not in ('unittest','pytest') or record['plan']['framework']!=framework:raise ValueError('La repetición individual requiere la misma suite Python.')
        failed=[r for r in (record.get('result') or {}).get('results',[]) if r.get('status') in ('failed','error')]
        if not failed:raise ValueError('No hay pruebas fallidas que repetir.')
        inventory={row['id'] for row in self.discover(ws)['tests']};selected=[]
        for row in failed:
            value=row.get('selector') or (row.get('id') if framework=='pytest' else None)
            if not isinstance(value,str) or '::' not in value:raise ValueError('Un fallo de importación no puede seleccionarse. Repite la suite completa.')
            path,member=value.split('::',1);base=path+'::'+member.split('[',1)[0].replace('::','.')
            if base not in inventory:raise ValueError('Una prueba cambió de nombre o ubicación. Descubre y revisa la suite completa.')
            selected.append(value)
        return list(dict.fromkeys(selected))
    def plan(self,ws,body,output=None):
        framework=body.get('framework','unittest');selection=body.get('selection','');coverage=body.get('coverage') is True
        if framework not in ('unittest','pytest','cargo','ctest','ncc'):raise ValueError('Motor de pruebas no admitido.')
        if selection and not any(x['id']==selection and (x['framework']==framework or framework=='pytest' and x['framework']=='unittest') for x in self.discover(ws)['tests']):raise ValueError('Selecciona una prueba del inventario actual.')
        if coverage and framework not in ('unittest','pytest'):raise ValueError('Esta integración de cobertura requiere Python y coverage instalado.')
        selections=self.failed_selections(ws,body['failedRun'],framework) if body.get('failedRun') else [selection] if selection else []
        output=Path(output) if output else ws.root/'.lumen/testing/<sesión>/results.json';prepare=[]
        if framework in ('unittest','pytest'):
            argv=[*python_command(ws,self.features.runtimes.config.get('tools')),str(Path(__file__).with_name('test_bridge.py')),'--workspace',str(ws.root),'--output',str(output),'--framework',framework]
            for selected in selections:
                file,member=selected.split('::',1);base,bracket,parameters=member.partition('[');member=(base.replace('.','::') if '::' not in base else base)+bracket+parameters
                argv+=['--selection',file+'::'+member if framework=='pytest' else selected]
            if coverage:argv+=['--coverage']
        elif framework=='cargo':
            if selection:raise ValueError('Cargo ejecuta la suite completa en esta integración.')
            cargo=find_tool('cargo',self.features.runtimes.config.get('tools'))
            if not cargo or not ws.resolve('Cargo.toml',must_exist=False).is_file():raise ValueError('Se necesitan Cargo y Cargo.toml.')
            rustc=find_tool('rustc',self.features.runtimes.config.get('tools'));options=['--config','build.rustc='+json.dumps(rustc)] if rustc else []
            prepare=[[cargo,'test','--no-run','--color','never',*options]];argv=[cargo,'test','--color','never',*options,'--','--format','pretty']
        elif framework=='ncc':
            entries=[row for row in self.discover(ws)['tests'] if row['framework']=='ncc' and (not selection or row['id']==selection)]
            if not entries:raise ValueError('No hay una entrada main nC para comprobar.')
            if len(entries)>1 and not selection:raise ValueError('Selecciona una entrada nC: cada prueba de humo ejecuta su main.')
            compiler=self.features.runtimes.executable('ncc')
            from .nc_project_bridge import backend_python
            argv=[*backend_python(),str(Path(__file__).with_name('nc_test_bridge.py')),'--workspace',str(ws.root),'--output',str(output),'--compiler',compiler]
            for entry in entries:argv+=['--source',entry['path']]
        else:
            if selection:raise ValueError('CTest ejecuta la suite completa en esta integración.')
            directories=self.discover(ws)['ctestDirectories'];directory=body.get('directory') or (directories[0] if len(directories)==1 else None)
            if directory not in directories:raise ValueError('Selecciona el directorio CMake de pruebas del inventario actual.')
            folder=ws.resolve(directory);ctest=find_tool('ctest',self.features.runtimes.config.get('tools'))
            if not folder or not ctest:raise ValueError('Configura primero un directorio CMake con pruebas y CTest instalado.')
            if body.get('build') is True:
                cmake=find_tool('cmake',self.features.runtimes.config.get('tools'))
                if not cmake:raise ValueError('CMake no está instalado.')
                prepare=[[cmake,'--build',str(folder)]]
            argv=[ctest,'--test-dir',str(folder),'--output-on-failure','--output-junit',str(output.with_suffix('.xml'))]
        return {'framework':framework,'commands':prepare+[argv],'preparation':len(prepare),'coverage':coverage,'selection':selection,'selections':selections,'directory':body.get('directory'),'note':'NCC comprueba parser, tipos, contratos y ejecuta main: es una prueba de humo, no una suite de aserciones.' if framework=='ncc' else 'Las pruebas ejecutan código del proyecto; Cargo puede descargar dependencias.'}
    def start(self,ws,body,context=None):
        if not ws.trusted or body.get('consent') is not True:raise PermissionError('Revisa y autoriza las órdenes de prueba.')
        request={key:body.get(key) for key in ('framework','selection','coverage','build','failedRun','directory')}
        with self.lock:
            existing=next((x for x in self.runs.values() if x['workspace']==str(ws.root) and self.active(x)),None)
            if existing:
                if existing['request']!=request or existing.get('context')!=context:raise ValueError('Otra suite de pruebas está en curso. Deténla o espera su resultado.')
                if not existing.get('job'):raise ValueError('La suite de pruebas se está preparando. Espera un momento.')
                return {'run':existing['id'],'job':existing['job'],'reused':True}
            for old in list(self.runs):
                if len(self.runs)<20:break
                if not self.active(self.runs[old]):self.runs.pop(old)
            identity=uuid.uuid4().hex;folder=ws.private_dir('testing/'+identity);output=folder/'results.json';plan=self.plan(ws,body,output)
            sources=self.source_hashes(ws)
            evidence=self.features.investigations.capture_optional(ws,plan['commands'])
            from .execution_evidence import runtime_signature
            record={'id':identity,'workspace':str(ws.root),'plan':plan,'request':request,'context':context,'created':time.time(),'jobs':[],'processes':[],'result':None,'folder':folder,'scheduling':True,'runtimeSignature':runtime_signature(self.features.runtimes),'environment':getattr(ws,'environment_path',None)}
            self.runs[identity]=record
            record['evidence']=evidence
        dependencies=[]
        try:
            for index,command in enumerate(plan['commands']):
                preparation=index<plan['preparation']
                def perform(event,command=command,preparation=preparation):
                    task=self.features.app.runner.start([command],ws.root,timeout=900,resource_class='background');record['processes'].append(task['job']);job=self.features.app.runner.jobs[task['job']]
                    while not job.done:
                        if event.wait(.1):job.cancel()
                    if preparation:
                        if job.code:raise ValueError('La preparación de pruebas falló. '+job.output[-2000:])
                        return {'process':job.id,'code':job.code}
                    result=self.read_result(ws,plan,output,job)
                    result['sourceHashes']=sources;current_sources=self.source_hashes(ws);result['sourcesChanged']=sorted(name for name in set(sources)|set(current_sources) if sources.get(name)!=current_sources.get(name))
                    if context:
                        changed=[]
                        for name,expected in context.get('expected',{}).items():
                            file=Path(name) if Path(name).is_absolute() else ws.resolve(name,must_exist=False)
                            actual=hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() and file.stat().st_size<=32*1024**2 else None
                            if actual!=expected:changed.append(name)
                        result['contextChanged']=changed
                    record['result']=result;atomic_json(folder/'run.json',self.public(record))
                    if job.code or result.get('error'):raise ValueError(result.get('error') or 'Las pruebas terminaron con código '+str(job.code)+'. Consulta los resultados del explorador.')
                    return {'run':identity,'summary':result.get('summary'),'code':job.code}
                task=self.features.hilo.submit(('Preparar pruebas' if preparation else 'Ejecutar pruebas')+' · '+plan['framework'],perform,workspace=ws.root,depends=dependencies,key='tests:'+identity+':'+str(index))
                record['jobs'].append(task['job']);dependencies=[task['job']]
            record['job']=dependencies[-1];record['scheduling']=False;return {'run':identity,'job':record['job'],'reused':False,'plan':plan}
        except BaseException:self.runs.pop(identity,None);raise
    def active(self,record):return record.get('scheduling') is True or any(x['id'] in record['jobs'] and x['state'] in ('queued','running') for x in self.features.hilo.snapshot(record['workspace'])['jobs'])
    def read_result(self,ws,plan,output,job):
        if plan['framework'] in ('unittest','pytest','ncc'):
            if not output.is_file() or output.stat().st_size>8*1024**2:return {'results':[],'summary':{},'error':'El intérprete no produjo un informe de pruebas válido.','output':job.output[-24000:],'code':job.code}
            data=json.loads(output.read_text(encoding='utf-8'));data['output']=job.output[-24000:];return data
        items=[]
        if plan['framework']=='ctest' and output.with_suffix('.xml').is_file():
            if output.with_suffix('.xml').stat().st_size>8*1024**2:raise ValueError('Informe CTest demasiado grande.')
            root=ET.parse(output.with_suffix('.xml')).getroot()
            for case in root.iter('testcase'):
                failure=next((child for child in case if child.tag in ('failure','error')),None);items.append({'id':case.get('name'),'name':case.get('name'),'status':'failed' if failure is not None else 'skipped' if case.find('skipped') is not None else 'passed','path':None,'line':1,'seconds':float(case.get('time','0')),'message':(failure.text or '')[-12000:] if failure is not None else ''})
        elif plan['framework']=='cargo':
            for match in re.finditer(r'(?m)^test (\S+) \.\.\. (ok|FAILED|ignored)',job.output):items.append({'id':match[1],'name':match[1],'status':{'ok':'passed','FAILED':'failed','ignored':'skipped'}[match[2]],'path':None,'line':1,'seconds':0,'message':''})
        return {'results':items,'summary':{status:sum(x['status']==status for x in items) for status in ('passed','failed','error','skipped')},'output':job.output[-24000:],'code':job.code}
    @staticmethod
    def public(record):return {k:v for k,v in record.items() if k!='folder'}
    def snapshot(self,ws,identity=None):
        with self.lock:
            records=[x for x in self.runs.values() if x['workspace']==str(ws.root) and (not identity or x['id']==identity)]
            states={x['id']:x for x in self.features.hilo.snapshot(ws.root)['jobs']}
            completed=any(x.get('result') for x in records)
            current=None;limited=False
            if completed:
                stamps=[];size=0
                for name in ws.files():
                    file=ws.resolve(name)
                    if file.suffix.lower() not in SUFFIXES|{'.toml'} and file.name not in BUILD_FILES:continue
                    try:s=file.stat();stamps.append((name,s.st_mtime_ns,s.st_ctime_ns,s.st_size));size+=s.st_size;limited|=s.st_size>1000000
                    except OSError:limited=True
                limited|=size>8*1024**2
                signature=hashlib.sha256(json.dumps(stamps).encode()).hexdigest()
                current=self.features.hilo.cached(('test-source-hashes',str(ws.root),signature),lambda:self.source_hashes(ws),ttl=60)
            from .execution_evidence import runtime_signature
            runtime=runtime_signature(self.features.runtimes);rows=[]
            for x in records[-20:]:
                recorded=(x.get('result') or {}).get('sourceHashes',{});changed=sorted(name for name in set(recorded)|set(current or {}) if recorded.get(name)!=(current or {}).get(name)) if x.get('result') else []
                environmentChanged=x.get('runtimeSignature')!=runtime or x.get('environment')!=getattr(ws,'environment_path',None)
                rows.append({**self.public(x),'active':self.active(x),'state':states.get(x.get('job'),{}).get('state','queued'),'error':states.get(x.get('job'),{}).get('error'),'changedSinceRun':changed,'sourceScopeLimited':limited,'stale':bool(changed or environmentChanged or (x.get('result') or {}).get('sourcesChanged')),'environmentChanged':environmentChanged})
            return {'runs':rows}
    def coverage(self,ws,identity):
        record=self.runs.get(identity)
        if not record or record['workspace']!=str(ws.root):raise ValueError('Informe de cobertura de otro proyecto.')
        path=record['folder']/'results.coverage.json'
        if not path.is_file() or path.stat().st_size>8*1024**2:raise ValueError('No hay cobertura disponible para esta ejecución.')
        return json.loads(path.read_text(encoding='utf-8'))
    def cancel(self,ws,identity):
        record=self.runs.get(identity)
        if not ws.trusted or not record or record['workspace']!=str(ws.root):raise PermissionError('Ejecución de pruebas de otro proyecto.')
        for identity in reversed(record['jobs']):self.features.hilo.cancel(identity)
        return {'cancelled':True}
