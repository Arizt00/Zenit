"""Opt-in Yjs-compatible shared buffers and one host execution environment.

No listener or guest process exists until the user starts a team session. The
transport uses one asyncio thread, not one polling worker per participant.
"""
import asyncio
import base64
from collections import OrderedDict
import hmac
import hashlib
from http.client import IncompleteRead
import json
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from urllib.error import HTTPError,URLError


def encode(value):return base64.b64encode(value).decode('ascii')
def decode(value,limit=524288):
    if not isinstance(value,str) or len(value)>limit*1.4:raise ValueError('La actualización supera el límite de tamaño.')
    return base64.b64decode(value,validate=True)


class TeamRoom:
    def __init__(self,features,workspace,documents,allow_run=False,protocol=1,share_project=False):
        from pycrdt import Doc,Text
        self.features=features;self.workspace=workspace;self.documents={};self.revisions={};self.peers={};self.lock=threading.RLock();self.jobs=set();self.allow_run=bool(allow_run);self.closed=False
        self.id=secrets.token_hex(12);self.token=secrets.token_urlsafe(32);self.checkpoints=[];self.executions={};self.run_requests=OrderedDict()
        self.run_seen=set()
        from .team_project import TeamProject
        self.project=TeamProject(self,protocol,share_project)
        self.add_documents(documents)

    def add_documents(self,documents):
        from pycrdt import Doc,Text
        maximum=128 if self.project.protocol==2 else 32
        if not isinstance(documents,list) or not (0 if self.project.shared else 1)<=len(documents)<=maximum:raise ValueError('La selección supera el presupuesto de archivos de esta sesión.')
        additions={}
        for item in documents:
            disk=self.workspace.read(item['path']);name=disk['path']
            if name in self.documents:continue
            if disk.get('binary'):raise ValueError('Comparte un archivo de texto.')
            text=item.get('text',disk['content'])
            if not isinstance(text,str) or len(text.encode('utf-8'))>500000:raise ValueError('El archivo compartido supera 500 KB.')
            additions[name]=(text,disk['revision'])
        if len(self.documents)+len(additions)>maximum:raise ValueError('La sesión alcanzó su presupuesto de documentos abiertos.')
        if sum(len(str(d['text']).encode('utf-8')) for d in self.documents.values())+sum(len(t.encode('utf-8')) for t,_ in additions.values())>8000000:raise ValueError('La sesión supera 8 MB de texto compartido.')
        for name,(text,revision) in additions.items():self.documents[name]=Doc({'text':Text(text)},allow_multithreading=True);self.revisions[name]=revision;self.project.register(name,text)
        return {'paths':list(self.documents),'room':self.id}

    def execution_snapshot(self):
        runner=self.features.app.runner
        self.jobs.intersection_update(runner.jobs)
        return {path:{**item,'done':not (job:=runner.jobs.get(item['job'])) or job.done,'code':job.code if job else None,'queued':getattr(job,'queued',False),'available':job is not None} for path,item in self.executions.items()}

    def request(self,body,owner=False):
        with self.lock:
            if self.closed:raise ValueError('La sesión ha terminado.')
            action=body.get('action','sync')
            identity=self.project.authenticate(body,owner)
            result=self.project.action(action,body,identity,owner)
            if result is not None:return result
            if action=='sync':
                peer=body.get('peer');name=body.get('name','Invitado')
                if not isinstance(peer,str) or not 1<=len(peer)<=100:raise ValueError('Participante inválido.')
                now=time.monotonic();self.peers={k:v for k,v in self.peers.items() if now-v['seen']<45}
                cursor=body.get('cursor');cursor={k:v for k,v in cursor.items() if k in ('lineNumber','column') and type(v) is int and 0<v<2000000} if isinstance(cursor,dict) else None
                self.peers[peer]={'id':peer,'name':str(name)[:80],'station':str(body.get('station','Navegador'))[:100],'path':str(body.get('path',''))[:300],'cursor':cursor,'seen':now}
                accepted=identity['permissions']['edit']
                incoming=body.get('updates',{}) if accepted else {}
                previous={}
                try:
                    for original_path,value in incoming.items():
                        path=self.project.resolve(original_path,body.get('documentIds'))
                        if path not in self.documents:raise PermissionError('El archivo no está compartido.')
                        doc=self.documents[path];previous.setdefault(path,doc.get_update())
                        doc.apply_update(decode(value))
                        if len(str(doc['text']).encode('utf-8'))>500000 or len(doc.get_update())>4000000:raise ValueError('El búfer compartido supera su presupuesto de memoria.')
                    if previous and (sum(len(str(doc['text']).encode()) for doc in self.documents.values())>8000000 or sum(len(doc.get_update()) for doc in self.documents.values())>16000000):raise ValueError('La sesión alcanzó su presupuesto de memoria compartida. Crea un punto de control y una sesión nueva.')
                except BaseException:
                    from pycrdt import Doc,Text
                    for path,update in previous.items():
                        doc=Doc({'text':Text()},allow_multithreading=True);doc.apply_update(update);self.documents[path]=doc
                    raise
                vectors={self.project.resolve(path,body.get('documentIds')):value for path,value in body.get('vectors',{}).items()}
                updates={path:encode(doc.get_update(decode(vectors[path],100000) if vectors.get(path) else None)) for path,doc in self.documents.items()}
                return {'room':self.id,'updates':updates,'acceptedUpdates':accepted,'paths':list(self.documents),'executions':self.execution_snapshot(),'peers':[{k:v for k,v in peer.items() if k!='seen'} for peer in self.peers.values()],'allowRun':self.allow_run,'environment':self.environment(),'checkpoints':[{'id':c['id'],'label':c['label'],'created':c['created']} for c in self.checkpoints],**self.project.public(body,identity)}
            if action=='share':
                if not owner:raise PermissionError('Solo el anfitrión añade archivos a la sesión.')
                return self.add_documents(body.get('documents'))
            if action=='checkpoint':
                self.project.require(identity,'edit')
                texts={p:str(d['text']) for p,d in self.documents.items()}
                if sum(len(t.encode('utf-8')) for t in texts.values())>2000000:raise ValueError('El punto de control admite hasta 2 MB de texto.')
                item={'id':secrets.token_hex(8),'label':str(body.get('label','Punto de equipo'))[:80],'created':time.time(),'texts':texts,'documentIds':dict(self.project.document_ids)};self.checkpoints=(self.checkpoints+[item])[-4:]
                return {k:v for k,v in item.items() if k!='texts'}
            if action=='restore':
                if not owner:raise PermissionError('El anfitrión restaura los puntos de control compartidos.')
                item=next((c for c in self.checkpoints if c['id']==body.get('id')),None)
                if not item:raise ValueError('El punto de control ya no existe.')
                for original_path,text in item['texts'].items():
                    path=self.project.resolve(original_path,item.get('documentIds'))
                    with self.documents[path].transaction():self.documents[path]['text'].clear();self.documents[path]['text'].insert(0,text)
                return {'restored':True}
            if action=='leave':self.peers.pop(body.get('peer'),None);return {'left':True}
            if action=='save':
                self.project.require(identity,'save')
                return self.save(self.project.resolve(body.get('path'),body.get('documentIds')))
            if action=='run':
                self.project.require(identity,'run')
                path=self.project.resolve(body.get('path'),body.get('documentIds'));request_id=body.get('requestId')
                if path not in self.documents:raise PermissionError('El archivo no está compartido.')
                if request_id is not None and (not isinstance(request_id,str) or not 1<=len(request_id)<=120):raise ValueError('Identificador de ejecución inválido.')
                if request_id in self.run_requests:
                    previous=self.run_requests[request_id]
                    if previous.get('document',self.project.document_ids.get(previous['path']))!=self.project.document_ids.get(path):raise ValueError('La petición de ejecución pertenece a otro archivo.')
                    if previous['job'] not in self.features.app.runner.jobs:raise ValueError('La ejecución anterior ya no está disponible; no se volverá a iniciar por este reintento.')
                    return {**previous,'reused':True}
                if request_id and hashlib.sha256(request_id.encode()).digest() in self.run_seen:raise ValueError('La petición anterior ya no está disponible; este reintento no iniciará otro proceso.')
                if len(self.run_seen)>=65536:raise ValueError('El registro de ejecución alcanzó su presupuesto. Termina esta sesión antes de crear otra.')
                previous=self.execution_snapshot().get(path)
                if previous and not previous['done']:
                    result={**previous,'path':path,'reused':True}
                else:
                    self.save(path);plan=self.features.runtimes.plan(self.workspace,path)
                    if plan.get('preview'):raise ValueError('Usa una tarea de consola en esta sesión.')
                    result={**self.features.app.runner.start(plan['commands'],self.workspace.root,timeout=0),'path':path,'started':time.time(),'reused':False}
                    self.jobs.add(result['job']);self.executions[path]={key:result[key] for key in ('job','started')}
                if request_id:
                    result['document']=self.project.document_ids[path];self.run_seen.add(hashlib.sha256(request_id.encode()).digest())
                    self.run_requests[request_id]=result
                    while len(self.run_requests)>128:self.run_requests.popitem(last=False)
                return result
            if action in ('job','stop','input'):
                job_id=body.get('job')
                if job_id not in self.jobs:raise PermissionError('Esta ejecución no pertenece al equipo.')
                job=self.features.app.runner.jobs.get(job_id)
                if job is None:raise ValueError('La ejecución ya no está disponible.')
                if action!='job':self.project.require(identity,'run')
                if action=='stop':job.cancel();return {'stopped':True}
                if action=='input':job.write(str(body.get('text',''))[:65536]);return {'sent':True}
                with job.lock:
                    output=job.output;offset=min(len(output),max(0,int(body.get('offset',0))));end=min(len(output),offset+50000)
                    return {'output':output[offset:end],'offset':end,'more':end<len(output),'done':job.done,'code':job.code,'queued':getattr(job,'queued',False)}
            raise ValueError('Acción de equipo desconocida.')

    def save(self,path):
        if path not in self.documents:raise PermissionError('El archivo no está compartido.')
        doc=self.documents[path];text=str(doc['text']);disk=self.workspace.read(path)
        buffer=self.features.buffers.items.get(path)
        if buffer and buffer['text'].replace('\r\n','\n') not in (text.replace('\r\n','\n'),disk['content'].replace('\r\n','\n')):raise ValueError('El archivo tiene cambios fuera de CoCo en otro búfer. Revisa ambas versiones antes de guardar.')
        if disk['revision']!=self.revisions[path]:
            if disk['content']!=text:raise ValueError('El archivo cambió fuera del equipo. Se conserva el búfer compartido; revisa ambos antes de guardar.')
        else:self.workspace.save(path,text,disk['revision'],newline=disk['newline'],bom=disk['bom'])
        result=self.workspace.read(path);self.revisions[path]=result['revision']
        if buffer:self.features.buffers.items[path]={**buffer,'text':text,'revision':result['revision'],'saved':True,'sequence':buffer['sequence']+1}
        return {'saved':True,'path':path,'text':text,'revision':result['revision']}

    def environment(self):
        active=next((s for s in self.features.tern.sessions.values() if s.get('active') and s['workspace']==str(self.workspace.root)),None)
        return {'workspace':self.workspace.root.name,'host':socket.gethostname(),'runtime':'Lantern' if active else 'Proyecto','shared':True}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('La invitación no puede redirigir a otro servidor.')


class TeamService:
    def __init__(self,features):self.features=features;self.room=None;self.remote=None;self.remote_room=None;self.remote_identity=None;self.remote_protocol=1;self.thread=None;self.loop=None;self.server=None;self.url=None;self.tunnel=None;self.mode='local';self.internet_job=None
    def start(self,ws,body):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de compartirlo.')
        mode=body.get('mode','lan' if body.get('network') else 'local')
        if mode not in ('local','lan','internet'):raise ValueError('Selecciona este equipo, red local o Internet.')
        self.stop();self.mode=mode;self.room=TeamRoom(self.features,ws,body.get('documents',[]),body.get('allowRun',False),body.get('protocol',1),body.get('shareProject',False));ready=threading.Event();errors=[]
        async def serve():
            try:self.server=await asyncio.start_server(self.client,'0.0.0.0' if self.mode=='lan' else '127.0.0.1',0,limit=8192);ready.set();await self.server.serve_forever()
            except asyncio.CancelledError:pass
            except Exception as error:errors.append(str(error));ready.set()
        def run():
            self.loop=asyncio.new_event_loop();asyncio.set_event_loop(self.loop)
            try:self.loop.run_until_complete(serve())
            finally:self.loop.close()
        self.thread=threading.Thread(target=run,name='zenit-team',daemon=True);self.thread.start()
        if not ready.wait(5) or errors:self.stop();raise ValueError('No se pudo abrir la sesión: '+str(errors))
        address='127.0.0.1'
        if self.mode=='lan':
            try:address=next(x[4][0] for x in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not x[4][0].startswith('127.'))
            except (StopIteration,OSError):address=socket.gethostname()
        self.url=f'http://{address}:{self.server.sockets[0].getsockname()[1]}/#{self.room.token}'
        if self.mode=='internet':self.internet()
        return self.status()

    def internet(self):
        if not self.room:raise ValueError('Crea la sesión compartida antes de conectar Internet.')
        if self.mode!='internet':raise ValueError('Selecciona Internet al crear la sesión para conectar otras redes.')
        if self.tunnel:self.tunnel.stop()
        from .coco_tunnel import InternetTunnel
        local='http://127.0.0.1:'+str(self.server.sockets[0].getsockname()[1])+'/'
        self.tunnel=InternetTunnel(self.features,local);tunnel=self.tunnel;self.mode='internet'
        try:result=self.features.hilo.submit('CoCo · conectar estaciones por Internet',tunnel.start,workspace=self.room.workspace.root,key='coco-internet:'+self.room.id+':'+secrets.token_hex(4),cancel=tunnel.stop,priority=1)
        except Exception as error:
            tunnel.stop();tunnel.phase='failed';tunnel.error=str(error);raise
        self.internet_job=result['job'];return result

    async def client(self,reader,writer):
        status=200;response={}
        try:
            head=await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
            lines=head.decode('latin1').split('\r\n');headers=dict(line.split(':',1) for line in lines[1:] if ':' in line);headers={k.lower():v.strip() for k,v in headers.items()}
            if lines[0].split()[0]=='GET':
                await self.asset(writer,lines[0].split()[1]);return
            if not self.room or not hmac.compare_digest(headers.get('authorization',''),'Bearer '+self.room.token):raise PermissionError('Invitación no válida o revocada.')
            if lines[0].split()[:2]!=['POST','/v1']:raise ValueError('Ruta desconocida.')
            size=int(headers.get('content-length','0'))
            if not 0<size<=2000000:raise ValueError('Petición demasiado grande.')
            body=json.loads(await asyncio.wait_for(reader.readexactly(size),8));response=self.room.request(body)
        except PermissionError as error:status=403;response={'error':str(error)}
        except Exception as error:status=400;response={'error':str(error)[:600]}
        raw=json.dumps(response,ensure_ascii=True).encode();writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n'.encode()+raw)
        try:await writer.drain()
        except (OSError,ConnectionError):pass
        finally:writer.close();await writer.wait_closed()

    async def asset(self,writer,value):
        from urllib.parse import unquote
        import mimetypes
        name=unquote(urlsplit(value).path).lstrip('/') or 'team.html';root=(self.features.app.project/'web').resolve()
        if name not in ('team.html','team-peer.js','team-peer.css','team-execution.js','coco-drafts.js') and not name.startswith(('vendor/monaco/','team-vendor/')):raise ValueError('Recurso no disponible.')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size>12000000:raise ValueError('Recurso no disponible.')
        data=path.read_bytes();mime=mimetypes.guess_type(name)[0] or 'application/octet-stream'
        if name.endswith(('.js','.mjs')):mime='application/javascript'
        policy="default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; worker-src 'self' blob:; img-src 'self' data:; font-src 'self' data:"
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: {mime}\r\nContent-Length: {len(data)}\r\nContent-Security-Policy: {policy}\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n'.encode()+data)
        await writer.drain();writer.close();await writer.wait_closed()

    def join(self,ws,url):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de unirte.')
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or not 32<=len(parsed.fragment)<=100 or parsed.path not in ('','/'):raise ValueError('Usa la invitación completa del anfitrión.')
        if self.room and hmac.compare_digest(parsed.fragment,self.room.token):raise ValueError('Ya eres el anfitrión de este equipo.')
        remote=(parsed._replace(fragment='',path='/v1').geturl(),parsed.fragment)
        identity=dict(self.remote_identity) if self.remote==remote and self.remote_identity else {'peer':secrets.token_hex(12)}
        result=self.contact(remote,{'action':'sync',**identity,'name':'Conectando','vectors':{}})
        if result.get('self',{}).get('resumeKey'):identity['resumeKey']=result['self']['resumeKey']
        self.stop();self.remote=remote;self.remote_identity=identity;self.remote_protocol=result.get('protocol',1);self.remote_room=result['room'];self.url=url;self.mode='internet' if parsed.scheme=='https' else 'local' if parsed.hostname in ('127.0.0.1','localhost','::1') else 'lan';return self.status()

    def contact(self,remote,body):
        endpoint,token=remote;request=Request(endpoint,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
        for attempt in range(2):
            try:
                with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=8) as response:
                    raw=response.read(32000000)
                    if len(raw)>=32000000:raise ValueError('Respuesta de equipo demasiado grande.')
                    result=json.loads(raw)
                break
            except HTTPError as error:
                try:message=json.loads(error.read(1000)).get('error')
                except Exception:message='No se pudo conectar con el equipo.'
                raise ValueError(message) from None
            except (URLError,TimeoutError,ConnectionError,IncompleteRead,json.JSONDecodeError):
                if attempt or body.get('action')!='run' or not body.get('requestId'):raise ValueError('El anfitrión no respondió. Puedes reintentar sin repetir la ejecución.') from None
        if result.get('error'):raise ValueError(result['error'])
        return result

    def request(self,body):
        body={**body,'station':socket.gethostname()}
        if self.remote:
            if self.remote_protocol==2:body.update(self.remote_identity)
            return self.contact(self.remote,body)
        if not self.room:raise ValueError('No hay sesión de equipo.')
        if self.room.project.protocol==2:body['peer']=self.room.project.owner
        result=self.room.request(body,owner=True)
        if body.get('action','sync')=='sync':result.update(connection=self.status()['connection'],invitation=self.status()['invitation'])
        return result
    def status(self):
        connection=self.tunnel.status() if self.tunnel else {'kind':self.mode,'phase':'ready' if self.room or self.remote else 'off','error':None}
        invitation=self.url
        if self.tunnel:invitation=connection['endpoint']+'/#'+self.room.token if connection['endpoint'] and self.room else None
        return {'active':bool(self.room or self.remote),'hosting':bool(self.room),'invitation':invitation,'room':self.room.id if self.room else self.remote_room,'allowRun':bool(self.room and self.room.allow_run),'station':socket.gethostname(),'connection':connection}
    def connector(self,target):
        import hashlib
        name={'vscode':'zenit-team-0.2.0.vsix','jetbrains':'zenit-team-jetbrains-0.1.0.zip'}.get(target)
        if not name:raise ValueError('Conector desconocido.')
        root=self.features.app.project
        path=next((p/name for p in (root/'integrations',root/'dist/integrations') if (p/name).is_file()),None)
        if not path:raise FileNotFoundError('Construye los conectores con tools/build_team_integrations.py.')
        data=path.read_bytes();return {'filename':name,'data':encode(data),'sha256':hashlib.sha256(data).hexdigest()}
    def stop(self):
        if self.internet_job:
            try:self.features.hilo.cancel(self.internet_job)
            except ValueError:pass
            self.internet_job=None
        if self.tunnel:self.tunnel.stop();self.tunnel=None
        if self.room:
            self.room.closed=True
            for identity in self.room.jobs:
                job=self.features.app.runner.jobs.get(identity)
                if job and not job.done:job.cancel()
        if self.loop and self.loop.is_running():
            def close():
                if self.server:self.server.close()
                for task in asyncio.all_tasks(self.loop):task.cancel()
            self.loop.call_soon_threadsafe(close)
        if self.thread and self.thread is not threading.current_thread():self.thread.join(timeout=5)
        self.room=None;self.remote=None;self.remote_room=None;self.loop=None;self.server=None;self.thread=None;self.url=None
        return self.status()
