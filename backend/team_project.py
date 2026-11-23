"""CoCo v2 project metadata and participant capabilities, separate from CRDT transport."""
import difflib,hashlib,hmac,os,re,secrets,time
from pathlib import Path
from .melody_files import MelodyFiles

class TeamProject:
    def __init__(self,room,protocol=1,shared=False):
        if protocol not in (1,2):raise ValueError('Versión de CoCo no admitida.')
        self.room=room;self.protocol=protocol;self.shared=bool(shared and protocol==2);self.members={};self.document_ids={};self.aliases={};self.tree_version=0;self.tree=[];self.events=[];self.baselines={};self.owner=secrets.token_hex(12)
        if self.shared:self.refresh()
    def permissions(self,role):
        return {'edit':role in ('host','editor','runner','legacy'),'tree':self.shared and role in ('host','editor','runner'),'save':role=='host' or role in ('runner','legacy') and self.room.allow_run,'run':role in ('host','runner','legacy') and self.room.allow_run,'manage':role=='host'}
    def authenticate(self,body,owner):
        peer=body.get('peer');action=body.get('action','sync')
        if self.protocol==1:return {'id':peer,'role':'host' if owner else 'legacy','permissions':self.permissions('host' if owner else 'legacy')}
        if owner:
            peer=peer or self.owner
            if not isinstance(peer,str) or not 1<=len(peer)<=100:raise ValueError('Participante inválido.')
            current=self.members.setdefault(peer,{'id':peer,'role':'host','created':time.time()})
            if current['role']!='host':raise PermissionError('El participante invitado no puede convertirse en anfitrión.')
            current.update(name=str(body.get('name',current.get('name','Anfitrión')))[:80],station=str(body.get('station',current.get('station','Zénit')))[:100],seen=time.monotonic())
            return {'id':peer,'role':'host','permissions':self.permissions('host')}
        if not isinstance(peer,str) or not 1<=len(peer)<=100:raise PermissionError('Actualiza el conector CoCo e identifica esta estación antes de continuar.')
        current=self.members.get(peer);new_key=None
        if current is None:
            if action!='sync':raise PermissionError('Conecta primero esta estación a CoCo.')
            if sum(len(str(m)) for m in self.members.values())>4000000:raise ValueError('La sesión alcanzó su presupuesto de participantes en memoria.')
            # A client-generated credential exists before the first response. Losing
            # that response must not strand the participant or create a second one.
            supplied=body.get('resumeKey')
            if supplied is not None and (not isinstance(supplied,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,100}',supplied)):raise ValueError('Credencial de reconexión inválida.')
            new_key=supplied or secrets.token_urlsafe(32);current={'id':peer,'role':'viewer','created':time.time(),'resumeHash':hashlib.sha256(new_key.encode()).hexdigest()};self.members[peer]=current
        elif current['role']=='host' or not isinstance(body.get('resumeKey'),str) or not hmac.compare_digest(current['resumeHash'],hashlib.sha256(body['resumeKey'].encode()).hexdigest()):raise PermissionError('La identidad de esta estación no coincide. Utiliza su credencial de reconexión o entra como una estación nueva.')
        current.update(name=str(body.get('name',current.get('name','Invitado')))[:80],station=str(body.get('station',current.get('station','Otra IDE')))[:100],seen=time.monotonic())
        result={'id':peer,'role':current['role'],'permissions':self.permissions(current['role'])}
        if new_key:result['resumeKey']=new_key
        return result
    def participants(self):
        now=time.monotonic()
        return [{k:m.get(k) for k in ('id','name','station','role')}|{'online':now-m.get('seen',0)<45} for m in self.members.values()]
    def require(self,identity,permission):
        if not identity['permissions'].get(permission):raise PermissionError('El anfitrión no ha concedido este permiso a tu estación: '+permission)
    def register(self,path,text):
        self.document_ids.setdefault(path,secrets.token_hex(12));self.baselines.setdefault(self.document_ids[path],text)
    def resolve(self,path,ids=None):
        if ids and path in ids:
            match=next((name for name,identity in self.document_ids.items() if identity==ids[path]),None)
            if match:return match
            raise PermissionError('El documento compartido ya no existe.')
        return self.aliases.get(path,path)
    def public(self,body,identity):
        data={'protocol':self.protocol,'self':identity,'participants':self.participants() if self.protocol==2 else [],'documents':[{'path':name,'id':value} for name,value in self.document_ids.items()],'project':{'shared':self.shared,'version':self.tree_version}}
        if self.shared and body.get('treeVersion')!=self.tree_version:data['project']['files']=self.tree
        return data
    def allowed(self,name):
        name,target=MelodyFiles.relative(self.room.workspace,name)
        if any(part.casefold() in ('build','dist','target','.idea','.pytest_cache','.mypy_cache','.ruff_cache') for part in Path(name).parts):raise PermissionError('Las carpetas generadas no se comparten como código del proyecto.')
        return name,target
    def refresh(self):
        rows=[]
        for name in self.room.workspace.files():
            try:
                _,file=self.allowed(name)
                if not file.is_file():continue
                with file.open('rb') as stream:sample=stream.read(8192)
                text=b'\x00' not in sample and file.stat().st_size<=500000
                if text:
                    try:sample.decode('utf-8-sig')
                    except UnicodeDecodeError:text=False
                rows.append({'path':name,'bytes':file.stat().st_size,'text':text})
            except (OSError,ValueError):continue
        self.tree=rows;self.tree_version+=1
    def event(self,kind,identity,**data):
        self.events.append({'kind':kind,'participant':identity['id'],'created':time.time(),**data});self.events=self.events[-256:];self.refresh()
    def action(self,action,body,identity,owner):
        room=self.room;ws=room.workspace
        if action=='permissions':
            self.require(identity,'manage');peer=body.get('participant');role=body.get('role');member=self.members.get(peer)
            if not member or member['role']=='host' or role not in ('viewer','editor','runner'):raise ValueError('Participante o permiso no válido.')
            if role=='runner' and not room.allow_run:raise PermissionError('Activa la ejecución compartida al crear la sesión antes de conceder este permiso.')
            member['role']=role;return {'updated':True,'participant':peer,'role':role}
        if action=='tree-refresh':
            if not self.shared:raise ValueError('Esta sesión comparte archivos individuales.')
            self.require(identity,'manage');self.refresh();return {'version':self.tree_version}
        if action=='project-open':
            if not self.shared:raise PermissionError('El árbol del proyecto no está compartido.')
            name,file=self.allowed(body.get('path'))
            if not any(x['path']==name and x['text'] for x in self.tree):raise PermissionError('Este archivo no está disponible como texto compartido.')
            return room.add_documents([{'path':name}])
        if action=='project-create':
            self.require(identity,'tree');name,file=self.allowed(body.get('path'));text=body.get('text','')
            if not isinstance(text,str) or len(text.encode())>500000 or '\x00' in text:raise ValueError('El archivo debe ser texto de hasta 500 KB.')
            if len(room.documents)>=128 or sum(len(str(d['text']).encode()) for d in room.documents.values())+len(text.encode())>8000000:raise ValueError('La sesión alcanzó su presupuesto de documentos abiertos.')
            with ws.lock:
                if file.exists():raise ValueError('El archivo ya existe; no se reemplaza.')
                ws.save(name,'',None,create=True);room.add_documents([{'path':name,'text':text}]);self.baselines[self.document_ids[name]]='';self.event('create',identity,path=name)
            return {'path':name,'id':self.document_ids[name]}
        if action=='project-rename':
            self.require(identity,'tree');old,source=self.allowed(body.get('path'));new,target=self.allowed(body.get('newPath'))
            if old not in room.documents:raise ValueError('Abre el archivo compartido antes de renombrarlo.')
            with ws.lock:
                if target.exists() or new in room.documents:raise ValueError('El destino ya existe; no se reemplaza.')
                if ws.read(old)['revision']!=room.revisions[old]:raise ValueError('El archivo cambió fuera de CoCo. Revisa ambas versiones antes de renombrarlo.')
                target.parent.mkdir(parents=True,exist_ok=True)
                if os.name=='nt':source.rename(target)
                else:
                    os.link(source,target,follow_symlinks=False)
                    if source.stat().st_ino!=target.stat().st_ino:target.unlink();raise ValueError('El origen cambió durante el renombrado.')
                    source.unlink()
                room.documents[new]=room.documents.pop(old);room.revisions[new]=room.revisions.pop(old);self.document_ids[new]=self.document_ids.pop(old)
                self.aliases={name:new if value==old else value for name,value in self.aliases.items()};self.aliases[old]=new;self.aliases.pop(new,None)
                if old in room.executions:room.executions[new]=room.executions.pop(old)
                self.event('rename',identity,path=old,newPath=new)
                self.room.features.extension_services.emit('zenit.tree.changed')
            return {'path':new,'oldPath':old,'id':self.document_ids[new]}
        if action=='review':
            changes=[]
            for name,doc in room.documents.items():
                before=self.baselines.get(self.document_ids[name],'');after=str(doc['text'])
                if before!=after:changes.append({'path':name,'before':before,'after':after,'diff':''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile=name+' · inicio',tofile=name+' · compartido'))[:1000000]})
            if sum(len(x['before'])+len(x['after']) for x in changes)>2000000:raise ValueError('Revisa los archivos en grupos; el conjunto supera 2 MB de texto.')
            return {'changes':changes,'events':self.events,'workspace':ws.root.name}
        return None
