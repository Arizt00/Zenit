"""Bounded provenance for a shared execution; never captures environment secrets."""
import hashlib,json,time
from pathlib import Path
from .execution_evidence import runtime_signature,context,compare

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def package_metadata(room):
    """Hash bounded package manifests in the project's Python environment only."""
    try:root=room.workspace.resolve(getattr(room.workspace,'environment_path','.venv'),must_exist=False)
    except (ValueError,OSError):return {'status':'unavailable'}
    if not root.is_dir():return None
    hasher=hashlib.sha256();count=0;total=0
    folders=[root/'Lib/site-packages',*sorted((root/'lib').glob('python*/site-packages'))]
    try:
        for folder in folders:
            if not folder.is_dir():continue
            for info in sorted(folder.glob('*.dist-info')):
                for name in ('METADATA','RECORD'):
                    file=info/name
                    if not file.is_file():continue
                    if not file.resolve().is_relative_to(root) or file.is_symlink():return {'status':'limited'}
                    size=file.stat().st_size;count+=1;total+=size
                    if count>2000 or total>6000000:return {'status':'limited'}
                    with file.open('rb') as stream:data=stream.read(min(size,6000000)+1)
                    if len(data)!=size:return {'status':'limited'}
                    hasher.update(file.relative_to(root).as_posix().encode());hasher.update(b'\0');hasher.update(hashlib.sha256(data).digest())
        return {'status':'recorded','files':count,'sha256':hasher.hexdigest()}
    except OSError:return {'status':'unavailable'}

def environment(room):
    ws=room.workspace
    active=next((s for s in room.features.tern.sessions.values() if s.get('active') and s['workspace']==str(ws.root)),None)
    receipt=None
    if active:
        directory,_=room.features.tern.owned(ws,active['id']);path=directory/'reconstruction.json'
        if path.is_file() and path.stat().st_size<16000:
            try:receipt=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
    return {'session':active['id'] if active else None,'kind':active['kind'] if active else 'project',
            'environmentId':receipt.get('environmentId') if isinstance(receipt,dict) else None,
            'bundleSha256':receipt.get('bundleSha256') if isinstance(receipt,dict) else None,
            'runtimeSignature':runtime_signature(room.features.runtimes),'pythonEnvironment':str(getattr(ws,'environment_path',None) or ''),
            'pythonPackageMetadata':package_metadata(room)}

def capture(room,path,plan,participant):
    source=room.workspace.read(path)
    commands=[list(c) if isinstance(c,(list,tuple)) else str(c) for c in plan['commands']]
    tools=[]
    for command in commands:
        if not isinstance(command,list) or not command:continue
        tool=Path(command[0])
        try:
            if tool.is_absolute() and tool.is_file():
                stat=tool.stat();tools.append({'path':str(tool),'bytes':stat.st_size,'modifiedNs':stat.st_mtime_ns})
        except OSError:pass
    record={'schema':1,'room':room.id,'path':path,'document':room.project.document_ids[path],'sourceSha256':digest(source['content']),
            'participant':participant,'recorded':time.time(),'commands':commands,'tools':tools,'environment':environment(room),
            'context':context(room.workspace,path,source['content']),
            'scope':'Archivo, fuentes y descriptores consultados, órdenes y metadatos del entorno Python del proyecto antes de iniciar. No congela herramientas, paquetes globales, datos externos ni variables; no verifica todos los bytes de dependencias instaladas.'}
    record['id']=digest(json.dumps(record,sort_keys=True,separators=(',',':')))
    return record

def describe(room,record):
    current=next((name for name,identity in room.project.document_ids.items() if identity==record['document']),record['path'])
    try:saved_matches=digest(room.workspace.read(current)['content'])==record['sourceSha256']
    except (ValueError,OSError):saved_matches=False
    shared_matches=current in room.documents and digest(str(room.documents[current]['text']))==record['sourceSha256']
    tools_match=True
    for tool in record['tools']:
        try:
            stat=Path(tool['path']).stat()
            if (stat.st_size,stat.st_mtime_ns)!=(tool['bytes'],tool['modifiedNs']):tools_match=False
        except OSError:tools_match=False
    try:verification=compare(record.get('context'),context(room.workspace,current,room.workspace.read(current)['content']))
    except (ValueError,OSError):verification={'status':'changed','notice':'El contexto guardado ya no está disponible.'}
    return {**record,'currentPath':current,'savedSourceMatches':saved_matches,'sharedSourceMatches':shared_matches,'sourceMatches':saved_matches and shared_matches,'toolsMatch':tools_match,'environmentMatches':environment(room)==record['environment'],'contextVerification':verification}
