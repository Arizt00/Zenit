"""A bounded, reviewable failure dossier grounded in source and actual IDE results."""
import difflib
from .change_footprint import footprint,sha

def dossier(features,ws,body):
    if not isinstance(body.get('diagnostics',[]),list):raise ValueError('Los diagnósticos deben ser una lista.')
    analysis=footprint(ws,body);path=analysis['path'];saved=ws.read(path)['content'];content=body.get('content',saved)
    sources=[{'path':path,'kind':'buffer','sha256':sha(content),'content':content[:16000],'truncated':len(content)>16000}]
    for name in analysis['dependencies'][:3]:
        text=ws.read(name)['content']
        sources.append({'path':name,'kind':'saved','sha256':sha(text),'content':text[:4000],'truncated':len(text)>4000})
    diagnostics=[]
    for row in body.get('diagnostics',[])[:30]:
        if isinstance(row,dict):diagnostics.append({k:str(row[k])[:1500] for k in ('message','source','severity','startLineNumber','startColumn') if k in row})
    state=features.lantern.snapshot();execution=None
    if features.lantern.workspace is ws and state.get('path')==path:
        history=state.get('history',[])
        job=features.lantern.job
        if job and job.done and state.get('executedGeneration')==state.get('generation'):
            execution={'revision':state['revision'],'code':job.code,'output':job.stream_output[-6000:],'log':job.output[-6000:], 'bufferSha256':getattr(job,'lantern_source_sha256',''),'outputSha256':job.stream_sha256,'complete':job.stream_complete and job.command_index==len(job.commands)-1,'cancelled':job.cancelled,'verification':state['verification'],
                'context':getattr(job,'lantern_context',None),'target':getattr(job,'lantern_destination',None),'environment':getattr(job,'lantern_environment',None),'commands':getattr(job,'lantern_commands',[]),'runtimeSha256':getattr(job,'lantern_runtime_sha256',None)}
        elif history:
            row=history[-1];execution={k:row.get(k) for k in ('revision','code','rawOutput','outputSha256','outputComplete','cancelled','sourceSha256','verification','context','target','environment','commands','runtimeSha256')}
            execution['bufferSha256']=row.get('sourceSha256','')
        if execution:execution['matchesBuffer']=execution.get('bufferSha256')==analysis['bufferSha256']
    from .runtimes import language
    destination=features.execution.selected(ws);lang=language(path,features.runtimes.config['languages'])
    if execution:
        from .execution_evidence import compare,runtime_signature
        execution['contextVerification']=compare(execution.pop('context',None),{'files':analysis['consulted'],'limited':analysis['limited']})
        execution['matchesTarget']=execution.get('target',{}).get('id')==destination['id'] if execution.get('target') else None
        execution['matchesEnvironment']=execution.get('environment')==getattr(ws,'environment_path',None)
        execution['matchesConfiguration']=execution.get('runtimeSha256')==runtime_signature(features.runtimes) if execution.get('runtimeSha256') else None
        complete=execution.get('complete',execution.get('outputComplete',False)) and not execution.get('cancelled')
        execution['currentEvidence']=bool(complete and execution['matchesBuffer'] and execution['matchesTarget'] and execution['matchesEnvironment'] and execution['matchesConfiguration'] and execution['contextVerification']['status']=='matched')
    environment={'target':{k:destination[k] for k in ('id','kind','label')},'language':lang,'pythonEnvironment':getattr(ws,'environment_path',None) if lang=='python' else None,'customAdapter':bool(features.runtimes.config['languages'].get(lang,{}).get('run') or features.runtimes.config['languages'].get(lang,{}).get('build')),'note':'El destino identifica dónde se ejecuta; no confirma que sus herramientas estén instaladas.'}
    return {'path':path,'environment':environment,'bufferSha256':analysis['bufferSha256'],'sources':sources,'diagnostics':diagnostics,'execution':execution,
        'diff':'\n'.join(difflib.unified_diff(saved.splitlines(),content.splitlines(),fromfile='Guardado',tofile='Búfer',n=2))[:8000],
        'references':{'dependencies':analysis['dependencies'],'affected':analysis['affected'][:20],'unresolved':analysis['unresolved'],'limited':analysis['limited']},
        'notice':'Revisa los archivos y resultados antes de preparar la consulta. Un resultado anterior se identifica por su huella; no demuestra el comportamiento del búfer actual. No se ha enviado información al modelo ni ejecutado código.'}
