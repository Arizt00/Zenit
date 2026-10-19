"""Three-way conflict review with index/blob and working-buffer revision guards."""
import hashlib,json,os,re,subprocess,threading,time,uuid
from pathlib import Path
from .runtime_paths import find_tool
from .terminals import child_environment
from .workspace import ConflictError
from .melody_files import MelodyFiles
from .preferences import atomic_json

class GitConflicts:
    def __init__(self,features):self.features=features;self.tickets={};self.lock=threading.RLock()
    def git(self,ws,args,limit=2*1024**2):
        git=find_tool('git')
        if not git:raise ValueError('Git no está instalado.')
        result=subprocess.run([git,'-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,'--no-pager',*args],cwd=ws.root,env=child_environment(),capture_output=True,timeout=12,creationflags=0x08000000 if os.name=='nt' else 0)
        if result.returncode:raise ValueError(result.stderr.decode('utf-8','replace')[-1500:] or 'No se pudo consultar Git.')
        if len(result.stdout)>limit:raise ValueError('La respuesta de Git supera el tamaño admitido.')
        return result.stdout
    def entries(self,ws,name=None):
        result={}
        for record in self.git(ws,['ls-files','--unmerged','-z','--',*([name] if name else [])]).split(b'\0'):
            if not record:continue
            metadata,raw=record.split(b'\t',1);mode,oid,stage=metadata.decode('ascii').split();path=raw.decode('utf-8')
            ws.resolve(path,must_exist=False)
            if not re.fullmatch('[a-f0-9]{40,64}',oid) or stage not in ('1','2','3'):raise ValueError('Entrada de conflicto inválida.')
            result.setdefault(path,{})[stage]={'oid':oid,'mode':mode}
        return result
    def snapshot(self,ws):
        try:entries=self.entries(ws)
        except ValueError as error:return {'available':False,'files':[],'message':str(error)}
        return {'available':True,'files':[{'path':path,'stages':list(stages),'kind':'both-modified' if '2' in stages and '3' in stages else 'modify-delete'} for path,stages in list(entries.items())[:500]]}
    @staticmethod
    def stamp(raw):return hashlib.sha256(raw).hexdigest() if raw is not None else None
    def read(self,ws,name):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para revisar sus conflictos.')
        with self.lock,ws.lock,self.features.buffers.lock:
            stages=self.entries(ws,name).get(name)
            if not stages:raise ValueError('El archivo ya no tiene un conflicto en el índice.')
            file=ws.resolve(name,must_exist=False);raw=file.read_bytes() if file.is_file() and file.stat().st_size<=2*1024**2 else None
            if file.exists() and raw is None:raise ValueError('El editor de conflictos admite hasta 2 MiB por archivo.')
            blobs={};binary=False
            for stage,label in [('1','base'),('2','ours'),('3','theirs')]:
                data=b''
                if stage in stages:
                    size=int(self.git(ws,['cat-file','-s',stages[stage]['oid']]).decode())
                    if size>2*1024**2:raise ValueError('Una versión del conflicto supera 2 MiB.')
                    data=self.git(ws,['cat-file','blob',stages[stage]['oid']])
                try:blobs[label]=data.decode('utf-8-sig');binary|=b'\x00' in data
                except UnicodeDecodeError:binary=True;blobs[label]=''
                binary|=stage in stages and stages[stage]['mode']=='120000'
            try:working=(raw or b'').decode('utf-8-sig');binary|=b'\x00' in (raw or b'')
            except UnicodeDecodeError:working='';binary=True
            buffer=self.features.buffers.items.get(name);working=buffer['text'] if buffer else working
            draft_path=ws.resolve('.lumen/conflict-drafts/'+hashlib.sha256(name.encode()).hexdigest()+'.json',must_exist=False);draft=None
            if draft_path.is_file() and draft_path.stat().st_size<=3*1024**2:
                try:
                    value=json.loads(draft_path.read_text(encoding='utf-8'))
                    if value.get('stages')==stages and value.get('before')==self.stamp(raw) and isinstance(value.get('content'),str):draft=value;working=value['content']
                except (OSError,ValueError):pass
            now=time.monotonic();self.tickets={k:v for k,v in self.tickets.items() if now-v['created']<900}
            if len(self.tickets)>=20:raise ValueError('Cierra una revisión de conflictos antes de abrir otra.')
            ticket=uuid.uuid4().hex;self.tickets[ticket]={'workspace':str(ws.root),'path':name,'stages':stages,'raw':raw,'buffer':dict(buffer) if buffer else None,'created':now,'binary':binary}
            return {'ticket':ticket,'path':name,**blobs,'result':working,'draft':bool(draft),'delete':bool(draft and draft.get('delete')),'oursDeleted':'2' not in stages,'theirsDeleted':'3' not in stages,'readOnly':binary,'message':'Este conflicto es binario o un enlace. Conserva sus versiones antes de resolverlo con una herramienta específica.' if binary else None}
    def draft(self,ws,body):
        if not ws.trusted:raise PermissionError('Proyecto no autorizado.')
        with self.lock:
            record=self.tickets.get(body.get('ticket'));text=body.get('content')
            if not record or record['workspace']!=str(ws.root) or record['binary']:raise ValueError('Revisión de conflictos no disponible.')
            if not isinstance(text,str) or len(text.encode())>2*1024**2 or '\x00' in text:raise ValueError('Borrador de conflictos inválido.')
            name=hashlib.sha256(record['path'].encode()).hexdigest()+'.json'
            atomic_json(ws.private_dir('conflict-drafts')/name,{'path':record['path'],'stages':record['stages'],'before':self.stamp(record['raw']),'content':text,'delete':body.get('delete') is True})
            return {'saved':True}
    def apply(self,ws,body):
        if not ws.trusted or body.get('consent') is not True:raise PermissionError('Revisa y guarda el resultado del conflicto.')
        with self.lock,ws.lock,self.features.buffers.lock:
            record=self.tickets.get(body.get('ticket'))
            if not record or record['workspace']!=str(ws.root) or time.monotonic()-record['created']>900:raise ValueError('La revisión caducó o pertenece a otro proyecto.')
            if record['binary']:raise ValueError('Este conflicto necesita una herramienta para archivos binarios.')
            name=record['path'];file=ws.resolve(name,must_exist=False);raw=file.read_bytes() if file.is_file() else None
            if self.stamp(raw)!=self.stamp(record['raw']) or self.entries(ws,name).get(name)!=record['stages']:raise ConflictError('El archivo o el índice cambió durante la revisión. Vuelve a abrir el conflicto.')
            buffer=self.features.buffers.items.get(name);previous=record['buffer']
            if (buffer or {}).get('text')!=(previous or {}).get('text'):raise ConflictError('El búfer cambió durante la revisión. Tu edición se conserva.')
            delete=body.get('delete') is True
            if delete and all(stage in record['stages'] for stage in ('2','3')):raise ValueError('La eliminación no forma parte de este conflicto.')
            text=body.get('content','')
            if not isinstance(text,str) or '\x00' in text or len(text.encode())>2*1024**2:raise ValueError('El resultado debe ser texto de hasta 2 MiB.')
            if body.get('stage') is True and re.search(r'(?m)^(?:<<<<<<< |=======\s*$|>>>>>>> )',text) and not delete:raise ValueError('Quedan marcadores de conflicto. Revisa el resultado antes de marcarlo resuelto.')
            recovery=ws.private_dir('conflicts')/(body['ticket']+'.before')
            if raw is not None:
                with recovery.open('xb') as out:out.write(raw)
            if delete:
                if file.exists():file.unlink()
                saved=None;self.features.buffers.items.pop(name,None)
            else:
                content=text.replace('\r\n','\n');new=content.replace('\n','\r\n').encode() if b'\r\n' in (raw or b'') else content.encode()
                if (raw or b'').startswith(b'\xef\xbb\xbf'):new=b'\xef\xbb\xbf'+new
                file.parent.mkdir(parents=True,exist_ok=True);MelodyFiles.replace(file,new);saved=self.stamp(new)
                if raw is None and any(x['mode']=='100755' for x in record['stages'].values()):file.chmod(0o755)
                if buffer:self.features.buffers.items[name]={**buffer,'text':content,'revision':saved,'saved':True,'sequence':buffer['sequence']+1}
            staged=False;warning=None
            if body.get('stage') is True:
                try:
                    if self.entries(ws,name).get(name)!=record['stages']:raise ConflictError('El índice cambió después de guardar el resultado.')
                    self.git(ws,['add','-A','--',name]);staged=True
                except ValueError as error:warning='El resultado se guardó, pero Git no lo marcó resuelto: '+str(error)
            self.tickets.pop(body['ticket']);ws.resolve('.lumen/conflict-drafts/'+hashlib.sha256(name.encode()).hexdigest()+'.json',must_exist=False).unlink(missing_ok=True)
            self.features.extension_services.emit('zenit.files.changed',paths=[name]);return {'saved':True,'staged':staged,'path':name,'revision':saved,'deleted':delete,'warning':warning,'recovery':str(recovery) if raw is not None else None}
