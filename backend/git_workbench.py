"""Reviewed local Git changes, using an alternate index and Git's index lock."""
import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from .runtime_paths import find_tool
from .terminals import child_environment
from .workspace import ConflictError

CONFLICTS={'DD','AU','UD','UA','DU','AA','UU'}


class GitWorkbench:
    def __init__(self,features):self.features=features;self.plans={};self.lock=threading.RLock()

    def git(self,ws,args,*,index=None,optional=False):
        tool=find_tool('git',self.features.runtimes.config.get('tools'))
        if not tool:raise ValueError('Configura Git en las herramientas del proyecto.')
        env=child_environment()
        if index:env['GIT_INDEX_FILE']=str(index)
        result=subprocess.run([tool,'--literal-pathspecs','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,'--no-pager',*args],cwd=ws.root,env=env,capture_output=True,timeout=15,creationflags=0x08000000 if os.name=='nt' else 0)
        if result.returncode:
            if optional:return None
            raise ValueError(result.stderr.decode('utf-8','replace')[-1500:] or 'Git no completó la operación.')
        if len(result.stdout)>4*1024*1024:raise ValueError('La respuesta de Git supera 4 MiB. Reduce el ámbito.')
        return result.stdout

    def index(self,ws):
        directory=Path(self.git(ws,['rev-parse','--absolute-git-dir']).decode().strip()).resolve()
        name=self.git(ws,['rev-parse','--git-path','index']).decode().strip()
        path=(ws.root/name).resolve()
        if path.parent!=directory or path.is_symlink():raise ValueError('Ruta de índice Git no admitida.')
        return path

    @staticmethod
    def stamp(path):
        if not path.exists():return None
        if not path.is_file() or path.stat().st_size>32*1024*1024:raise ValueError('El archivo excede el límite de revisión de Git.')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def snapshot(self,ws):
        try:
            if self.git(ws,['rev-parse','--show-prefix']).strip():return {'available':False,'files':[],'message':'Abre la raíz del repositorio para revisar y preparar sus cambios.'}
            raw=self.git(ws,['status','--porcelain=v1','-z','--untracked-files=all'])
            branch=self.git(ws,['symbolic-ref','--quiet','--short','HEAD'],optional=True)
        except ValueError as error:return {'available':False,'files':[],'message':str(error)}
        records=iter(raw.split(b'\0'));rows=[]
        for record in records:
            if not record:continue
            state=record[:2].decode('ascii');path=record[3:].decode('utf-8');old=None
            if 'R' in state or 'C' in state:old=next(records).decode('utf-8')
            ws.resolve(path,must_exist=False)
            if old:ws.resolve(old,must_exist=False)
            rows.append({'path':path,'oldPath':old,'status':state,'staged':state[0] not in (' ','?'),'working':state[1]!=' ' or state=='??','conflict':state in CONFLICTS})
            if len(rows)>2000:raise ValueError('Hay más de 2000 cambios. Reduce el proyecto antes de revisar el índice.')
        return {'available':True,'branch':branch.decode().strip() if branch else 'HEAD separado','files':rows}

    def blob(self,ws,path,head=False):
        args=['ls-tree','-z','HEAD','--',path] if head else ['ls-files','--stage','-z','--',path]
        data=self.git(ws,args,optional=head)
        if not data:return b''
        metadata=data.split(b'\t',1)[0].decode().split();oid=metadata[2] if head else metadata[1]
        return self.git(ws,['cat-file','blob',oid])

    def preview(self,ws,body):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para revisar el repositorio.')
        path=body.get('path');scope=body.get('scope','working');row=next((r for r in self.snapshot(ws)['files'] if r['path']==path),None)
        if not row or scope not in ('working','staged'):raise ValueError('Selecciona un cambio actual de Git.')
        if row['conflict']:raise ValueError('Abre el editor de conflictos para resolver este archivo.')
        index=self.index(ws);index_stamp=self.stamp(index);head=self.git(ws,['rev-parse','--verify','-q','HEAD'],optional=True)
        if scope=='working':
            file=ws.resolve(path,must_exist=False);before=self.blob(ws,path);after=file.read_bytes() if file.is_file() and file.stat().st_size<=1024*1024 else b''
            if file.exists() and (not file.is_file() or file.stat().st_size>1024*1024):raise ValueError('La revisión admite archivos de hasta 1 MiB.')
        else:before=self.blob(ws,row.get('oldPath') or path,head=True);after=self.blob(ws,path)
        if max(len(before),len(after))>1024*1024:raise ValueError('La revisión admite versiones de hasta 1 MiB.')
        try:
            a=before.decode('utf-8-sig').replace('\r\n','\n');b=after.decode('utf-8-sig').replace('\r\n','\n');binary=b'\0' in before+after
        except UnicodeError:a=b='';binary=True
        paths=list(dict.fromkeys([path,*([row['oldPath']] if row['oldPath'] else [])]));files={p:self.stamp(ws.resolve(p,must_exist=False)) for p in paths}
        if scope=='working':
            expected=hashlib.sha256(after).hexdigest() if file.is_file() else None
            if files[path]!=expected:raise ConflictError('El archivo cambió durante la revisión de Git.')
        identity=uuid.uuid4().hex;plan={'id':identity,'workspace':str(ws.root),'created':time.monotonic(),'path':path,'paths':paths,'scope':scope,'index':str(index),'indexStamp':index_stamp,'head':head,'files':files}
        if self.stamp(index)!=index_stamp:raise ConflictError('El índice cambió durante la revisión. Abre de nuevo el cambio.')
        with self.lock:
            self.plans={k:v for k,v in self.plans.items() if time.monotonic()-v['created']<600};self.plans[identity]=plan
            for key in list(self.plans)[:-20]:self.plans.pop(key)
        return {'id':identity,'path':path,'oldPath':row['oldPath'],'scope':scope,'before':a,'after':b,'binary':binary,'beforeBytes':len(before),'afterBytes':len(after),'action':'stage' if scope=='working' else 'unstage'}

    def apply(self,ws,body):
        if not ws.trusted or body.get('consent') is not True:raise PermissionError('Revisa primero el cambio del índice.')
        with self.lock,ws.lock:
            plan=self.plans.get(body.get('plan'))
            if not plan or plan['workspace']!=str(ws.root) or time.monotonic()-plan['created']>600:raise ValueError('La revisión de Git caducó.')
            index=self.index(ws)
            def guard():
                if self.stamp(index)!=plan['indexStamp'] or self.git(ws,['rev-parse','--verify','-q','HEAD'],optional=True)!=plan['head']:raise ConflictError('El índice o HEAD cambió. Revisa de nuevo el archivo.')
                if any(self.stamp(ws.resolve(p,must_exist=False))!=stamp for p,stamp in plan['files'].items()):raise ConflictError('El archivo cambió después de la revisión.')
                if plan['scope']=='working':
                    with self.features.buffers.lock:
                        if any((self.features.buffers.items.get(p) or {}).get('saved') is False for p in plan['paths']):raise ConflictError('Guarda el búfer antes de preparar su versión de disco en Git.')
            guard();descriptor,name=tempfile.mkstemp(prefix='zenit-index-',dir=index.parent);os.close(descriptor);temporary=Path(name);lock=index.with_name(index.name+'.lock');owned=False
            try:
                if index.exists():shutil.copyfile(index,temporary)
                else:temporary.unlink();self.git(ws,['read-tree','--empty'],index=temporary)
                if plan['scope']=='working':self.git(ws,['add','-A','--',*plan['paths']],index=temporary)
                elif plan['head']:self.git(ws,['reset','-q','HEAD','--',*plan['paths']],index=temporary)
                else:self.git(ws,['rm','--cached','--force','--ignore-unmatch','-q','--',*plan['paths']],index=temporary)
                # Git's lock excludes other Git writers. Never replace an index
                # that changed while the alternate index was being prepared.
                try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);owned=True
                except FileExistsError:raise ConflictError('Git está ocupado. Su índice no se ha modificado.')
                with os.fdopen(fd,'wb') as output:
                    guard();output.write(temporary.read_bytes());output.flush();os.fsync(output.fileno())
                os.replace(lock,index);owned=False;self.plans.pop(plan['id'],None)
            finally:
                temporary.unlink(missing_ok=True)
                temporary.with_name(temporary.name+'.lock').unlink(missing_ok=True)
                if owned:lock.unlink(missing_ok=True)
        self.features.extension_services.emit('zenit.files.changed',paths=plan['paths'])
        return {'applied':True,'action':'stage' if plan['scope']=='working' else 'unstage','path':plan['path']}
