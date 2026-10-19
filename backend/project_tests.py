"""Project tests: passive source discovery, reviewed argv and real result files."""
import ast,hashlib,json,re,threading,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
from .foundation import python_command
from .runtime_paths import find_tool
from .preferences import atomic_json

class ProjectTests:
    def __init__(self,features):self.features=features;self.runs={};self.lock=threading.RLock()
    def discover(self,ws):
        files=[];frameworks=[{'id':'unittest','label':'Python · unittest'},{'id':'pytest','label':'Python · pytest (requiere el paquete)'}]
        if ws.resolve('Cargo.toml',must_exist=False).is_file():frameworks.append({'id':'cargo','label':'Rust · Cargo'})
        if any(ws.resolve(p,must_exist=False).is_file() for p in ('build/CTestTestfile.cmake','.lumen/build/CTestTestfile.cmake')):frameworks.append({'id':'ctest','label':'C / C++ · CTest'})
        for name in ws.files():
            path=ws.resolve(name)
            if path.suffix!='.py' or not path.name.startswith('test') or path.stat().st_size>1000000:continue
            try:tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            except (SyntaxError,UnicodeError):continue
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):files.append({'id':name+'::'+node.name,'path':name,'line':node.lineno,'name':node.name,'framework':'pytest'})
                if isinstance(node,ast.ClassDef):
                    unit=any(isinstance(base,ast.Attribute) and base.attr=='TestCase' or isinstance(base,ast.Name) and base.id.endswith('TestCase') for base in node.bases)
                    for member in node.body:
                        if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)) and member.name.startswith('test') and (unit or node.name.startswith('Test')):files.append({'id':name+'::'+node.name+'.'+member.name,'path':name,'line':member.lineno,'name':node.name+'.'+member.name,'framework':'unittest' if unit else 'pytest'})
            if len(files)>5000:raise ValueError('El explorador admite hasta 5000 pruebas por proyecto.')
        return {'tests':files,'frameworks':frameworks,'discovery':'AST; no se importa ni ejecuta código del proyecto'}
    def plan(self,ws,body,output=None):
        framework=body.get('framework','unittest');selection=body.get('selection','');coverage=body.get('coverage') is True
        if framework not in ('unittest','pytest','cargo','ctest'):raise ValueError('Motor de pruebas no admitido.')
        if selection and not any(x['id']==selection and (x['framework']==framework or framework=='pytest') for x in self.discover(ws)['tests']):raise ValueError('Selecciona una prueba del inventario actual.')
        if coverage and framework not in ('unittest','pytest'):raise ValueError('Esta integración de cobertura requiere Python y coverage instalado.')
        output=Path(output) if output else ws.root/'.lumen/testing/<sesión>/results.json';prepare=[]
        if framework in ('unittest','pytest'):
            argv=[*python_command(ws,self.features.runtimes.config.get('tools')),str(Path(__file__).with_name('test_bridge.py')),'--workspace',str(ws.root),'--output',str(output),'--framework',framework]
            if selection:
                file,member=selection.split('::',1);argv+=['--selection',file+'::'+member.replace('.','::') if framework=='pytest' else selection]
            if coverage:argv+=['--coverage']
        elif framework=='cargo':
            if selection:raise ValueError('Cargo ejecuta la suite completa en esta integración.')
            cargo=find_tool('cargo',self.features.runtimes.config.get('tools'))
            if not cargo or not ws.resolve('Cargo.toml',must_exist=False).is_file():raise ValueError('Se necesitan Cargo y Cargo.toml.')
            prepare=[[cargo,'test','--no-run','--color','never']];argv=[cargo,'test','--color','never','--','--format','pretty']
        else:
            if selection:raise ValueError('CTest ejecuta la suite completa en esta integración.')
            folder=next((ws.resolve(name) for name in ('build','.lumen/build') if ws.resolve(name+'/CTestTestfile.cmake',must_exist=False).is_file()),None);ctest=find_tool('ctest')
            if not folder or not ctest:raise ValueError('Configura primero un directorio CMake con pruebas y CTest instalado.')
            if body.get('build') is True:
                cmake=find_tool('cmake')
                if not cmake:raise ValueError('CMake no está instalado.')
                prepare=[[cmake,'--build',str(folder)]]
            argv=[ctest,'--test-dir',str(folder),'--output-on-failure','--output-junit',str(output.with_suffix('.xml'))]
        return {'framework':framework,'commands':prepare+[argv],'preparation':len(prepare),'coverage':coverage,'selection':selection,'note':'Las pruebas ejecutan código del proyecto; Cargo puede descargar dependencias.'}
    def start(self,ws,body,context=None):
        if not ws.trusted or body.get('consent') is not True:raise PermissionError('Revisa y autoriza las órdenes de prueba.')
        request={key:body.get(key) for key in ('framework','selection','coverage','build')}
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
            record={'id':identity,'workspace':str(ws.root),'plan':plan,'request':request,'context':context,'created':time.time(),'jobs':[],'processes':[],'result':None,'folder':folder,'scheduling':True}
            self.runs[identity]=record
        dependencies=[]
        try:
            for index,command in enumerate(plan['commands']):
                preparation=index<plan['preparation']
                def perform(event,command=command,preparation=preparation):
                    task=self.features.app.runner.start([command],ws.root,timeout=900);record['processes'].append(task['job']);job=self.features.app.runner.jobs[task['job']]
                    while not job.done:
                        if event.wait(.1):job.cancel()
                    if preparation:
                        if job.code:raise ValueError('La preparación de pruebas falló. '+job.output[-2000:])
                        return {'process':job.id,'code':job.code}
                    result=self.read_result(ws,plan,output,job)
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
        if plan['framework'] in ('unittest','pytest'):
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
            return {'runs':[{**self.public(x),'active':self.active(x),'state':states.get(x.get('job'),{}).get('state','queued'),'error':states.get(x.get('job'),{}).get('error')} for x in records[-20:]]}
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
