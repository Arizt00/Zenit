"""Reviewed regression experiments on disposable copies with bounded sequential runs.

History contains source snapshots, not historical tool installations. Refuse an
attribution when the reviewed dependency context or runtime has changed.
"""
import json,shutil,tempfile,time
from pathlib import Path
from concurrent.futures import CancelledError
from .melody_countercheck import MelodyCountercheck,digest
from .execution_evidence import context,runtime_signature
from .lantern_adapters import stage,prepare,Superseded
from .workspace import Workspace

class LanternRegression(MelodyCountercheck):
    title='Lantern · Investigar un cambio'

    def history(self,ws,path):
        directory=ws.private_dir('lantern')/digest(path)[:24]
        file=directory/'history.json'
        if not file.is_file():return []
        if file.stat().st_size>2000000:raise ValueError('El historial de Lantern supera su presupuesto.')
        rows=json.loads(file.read_text(encoding='utf-8'))
        return [r for r in rows[-20:] if r.get('path')==path and r.get('replayAvailable') and type(r.get('revision')) is int and r['revision']>0]

    def plan(self,ws,body):
        mode=body.get('mode');path=body.get('path','')
        if mode not in ('first-change','reduce-input'):raise ValueError('Elige localizar el primer cambio o reducir una entrada.')
        saved=ws.read(path);content=body.get('content',saved['content']);timeout=body.get('timeout',5)
        if type(timeout) not in (int,float) or not 1<=timeout<=10:raise ValueError('Usa entre 1 y 10 segundos por ensayo.')
        result=super().plan(ws,{**body,'content':content,'timeout':timeout});plan=self.plans[result['id']]
        plan.update(mode=mode,runtimeSignature=runtime_signature(self.f.runtimes),environment=getattr(ws,'environment_path',None))
        reviewed=context(ws,path,content)
        if reviewed['limited']:raise ValueError('El contexto excede el presupuesto de revisión; abre una carpeta más pequeña.')
        plan['context']=reviewed
        if mode=='first-change':
            rows=self.history(ws,path);selected=body.get('revisions',[r['revision'] for r in rows][-10:])
            if not isinstance(selected,list) or not 2<=len(selected)<=10 or len(set(selected))!=len(selected) or any(type(r) is not int for r in selected):raise ValueError('Elige entre 2 y 10 revisiones guardadas distintas.')
            rows=[r for r in rows if r['revision'] in selected]
            if len(rows)!=len(selected):raise ValueError('Alguna revisión ya no tiene una copia reproducible. Vuelve a ejecutar el programa con Lantern.')
            directory=ws.private_dir('lantern')/digest(path)[:24];sources=[];dependencies={f['path']:f['sha256'] for f in reviewed['files'] if f['path']!=path}
            for row in sorted(rows,key=lambda r:r['revision']):
                old=row.get('context')
                if not old or old.get('limited') or {f['path']:f['sha256'] for f in old['files'] if f['path']!=path}!=dependencies or row.get('runtimeSha256')!=plan['runtimeSignature'] or row.get('environment')!=plan['environment']:raise ValueError('El contexto o las herramientas de esas revisiones cambiaron; no se atribuirá el fallo sólo al archivo.')
                file=directory/f"replay-{row['revision']}.json"
                if file.is_symlink() or file.stat().st_size>800000:raise ValueError('Copia de revisión inválida.')
                snapshot=json.loads(file.read_text(encoding='utf-8'));source=snapshot.get('source')
                if not isinstance(source,str) or len(source.encode())>128000 or digest(source)!=row.get('sourceSha256'):raise ValueError('La copia no coincide con la revisión registrada.')
                sources.append({'revision':row['revision'],'source':source,'sha256':digest(source)})
            plan['sources']=sources
        else:
            expected=body.get('expectedOutput');code=body.get('expectedExit',0)
            if not isinstance(expected,str) or len(expected.encode())>4096 or type(code) is not int or not -255<=code<=255:raise ValueError('Indica una salida esperada de hasta 4 KiB y un código de terminación válido.')
            if not plan['stdin']:raise ValueError('Indica la entrada que quieres reducir.')
            plan.update(expectedOutput=expected.replace('\r\n','\n'),expectedExit=code)
        return {**result,'mode':mode,'revisions':[{'revision':r['revision'],'sha256':r['sha256']} for r in plan.get('sources',[])],
                'budget':{'runs':32,'seconds':120},'notice':'Ensayos secuenciales en copias privadas, con la misma entrada y el contexto revisado. Repite cada observación; un resultado inestable impide atribuir una causa. No reconstruye herramientas históricas ni modifica el proyecto.'}

    def execute(self,ws,plan,event):
        if self.f.execution.reviewed_target(ws)!=plan['executionTarget'] or runtime_signature(self.f.runtimes)!=plan['runtimeSignature'] or getattr(ws,'environment_path',None)!=plan['environment']:raise ValueError('El destino o el entorno cambió después de revisar.')
        if ws.read(plan['path'])['revision']!=plan['revision']:raise ValueError('El archivo cambió después de revisar.')
        if context(ws,plan['path'],plan['content'])['files']!=plan['context']['files']:raise ValueError('Las dependencias revisadas cambiaron.')
        deadline=time.monotonic()+120;trials=[];unstable=False;budget=False
        with tempfile.TemporaryDirectory(prefix='zenit-regression-') as folder:
            root=Path(folder)
            try:base=stage(ws,plan['path'],plan['content'],root/'base',event.is_set)
            except Superseded:raise CancelledError()
            if context(base,plan['path'],plan['content'])['files']!=plan['context']['files']:raise ValueError('La copia no coincide con las dependencias revisadas.')
            def trial(source,stdin):
                nonlocal budget
                if event.is_set():raise CancelledError()
                if len(trials)>=32 or time.monotonic()>=deadline:budget=True;return None
                if self.f.execution.reviewed_target(ws)!=plan['executionTarget'] or runtime_signature(self.f.runtimes)!=plan['runtimeSignature'] or getattr(ws,'environment_path',None)!=plan['environment']:raise ValueError('La configuración del entorno cambió durante la investigación.')
                self.f.hilo.report(event,f'Ensayo {len(trials)+1}/32')
                with tempfile.TemporaryDirectory(prefix='trial-',dir=root) as target:
                    def copy(a,b):
                        if event.is_set():raise CancelledError()
                        return shutil.copy2(a,b)
                    shutil.copytree(base.root,target,dirs_exist_ok=True,copy_function=copy);shadow=Workspace(Path(target),ws.native);shadow.trusted=True;shadow.python_workspace=ws;shadow.reviewed_target=plan['executionTarget'];shadow.resolve(plan['path']).write_text(source,encoding='utf-8',newline='')
                    runtime=prepare(self.f.runtimes,shadow,plan['path']);commands=[*runtime['checks'],*runtime['commands']]
                    if not commands:raise ValueError('El adaptador no ejecuta programas por consola.')
                    run=self.f.app.runner.start(commands,shadow.root,timeout=min(plan['timeout'],max(.1,deadline-time.monotonic())),stdin=stdin,close_stdin=True,resource_class='background');job=self.f.app.runner.jobs[run['job']]
                    while not job.done:
                        if event.is_set():job.cancel()
                        event.wait(.04)
                    if event.is_set():raise CancelledError()
                    if job.cancelled or not job.stream_complete or job.command_index!=len(commands)-1:raise ValueError('Un ensayo no terminó o falló su preparación; no se atribuye una regresión.')
                    output=job.stream_output.replace('\r\n','\n')
                    row={'sourceSha256':digest(source),'inputSha256':digest(stdin),'code':job.code,'outputSha256':job.stream_sha256,'output':output[-4096:], 'matchesExpected':job.code==plan.get('expectedExit') and output==plan.get('expectedOutput')}
                    trials.append(row);return row
            def stable(source,stdin):
                nonlocal unstable
                a=trial(source,stdin);b=trial(source,stdin) if a else None
                if not b:return None
                if (a['code'],a['outputSha256'])!=(b['code'],b['outputSha256']):unstable=True;return None
                return a
            result={'mode':plan['mode'],'path':plan['path'],'executionTarget':plan['executionTarget'],'context':plan['context'],'sequential':True,'trials':trials,'scope':plan.get('notice','Copias locales revisadas; dos observaciones por candidato. No acredita determinismo general ni reconstruye herramientas históricas.')}
            if plan['mode']=='first-change':
                baseline=None;first=None;observations=[]
                for item in plan['sources']:
                    row=stable(item['source'],plan['stdin'])
                    if row is None:break
                    signature=(row['code'],row['outputSha256']);baseline=baseline or signature;different=signature!=baseline
                    observations.append({'revision':item['revision'],'sourceSha256':item['sha256'],'different':different,'code':row['code'],'outputSha256':row['outputSha256']})
                    if different and first is None:first=item['revision']
                result.update(firstChangedRevision=first if not unstable and not budget else None,observations=observations,status='unstable' if unstable else 'budget' if budget else 'changed' if first is not None else 'equivalent')
            else:
                candidate=plan['stdin'];initial=stable(plan['content'],candidate)
                if initial is None:result.update(status='unstable' if unstable else 'budget',reducedInput=candidate)
                elif initial['matchesExpected']:result.update(status='not-failing',reducedInput=candidate)
                else:
                    # Preserve this observed failure signature; a new crash is not
                    # an acceptable reduction of the original regression.
                    signature=(initial['code'],initial['outputSha256']);granularity=2
                    while candidate and not unstable and not budget:
                        width=max(1,(len(candidate)+granularity-1)//granularity);reduced=False
                        for start in range(0,len(candidate),width):
                            attempt=candidate[:start]+candidate[start+width:];row=stable(plan['content'],attempt)
                            if row is None:break
                            if (row['code'],row['outputSha256'])==signature:candidate=attempt;granularity=max(2,granularity-1);reduced=True;break
                        if not reduced:
                            if granularity>=len(candidate):break
                            granularity=min(len(candidate),granularity*2)
                    result.update(status='unstable' if unstable else 'budget' if budget else 'reduced',originalInputBytes=len(plan['stdin'].encode()),reducedInput=candidate,reducedInputSha256=digest(candidate),reducedInputBytes=len(candidate.encode()),minimality='Reducción por eliminación de fragmentos dentro del presupuesto; no garantiza un mínimo global.')
        return result
