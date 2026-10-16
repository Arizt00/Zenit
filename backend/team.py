"""Opt-in Yjs-compatible shared buffers and one host execution environment.

No listener or guest process exists until the user starts a team session. The
transport uses one asyncio thread, not one polling worker per participant.
"""
import asyncio
import base64
import hmac
import json
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from urllib.error import HTTPError


def encode(value):return base64.b64encode(value).decode('ascii')
def decode(value,limit=524288):
    if not isinstance(value,str) or len(value)>limit*1.4:raise ValueError('La actualización supera el límite de tamaño.')
    return base64.b64decode(value,validate=True)


class TeamRoom:
    def __init__(self,features,workspace,documents,allow_run=False):
        from pycrdt import Doc,Text
        self.features=features;self.workspace=workspace;self.documents={};self.revisions={};self.peers={};self.lock=threading.RLock();self.jobs=set();self.allow_run=bool(allow_run);self.closed=False
        self.id=secrets.token_hex(12);self.token=secrets.token_urlsafe(32);self.checkpoints=[]
        for item in documents:
            name=item['path'];disk=workspace.read(name)
            if disk.get('binary'):raise ValueError('Comparte un archivo de texto.')
            text=item.get('text',disk['content'])
            if not isinstance(text,str) or len(text.encode('utf-8'))>500000:raise ValueError('El archivo compartido supera 500 KB.')
            self.documents[name]=Doc({'text':Text(text)},allow_multithreading=True);self.revisions[name]=disk['revision']
        if not self.documents or len(self.documents)>32:raise ValueError('Selecciona entre uno y 32 archivos por sesión.')
        if sum(len(str(d['text']).encode('utf-8')) for d in self.documents.values())>8000000:raise ValueError('La sesión supera 8 MB de texto compartido.')

    def request(self,body,owner=False):
        with self.lock:
            if self.closed:raise ValueError('La sesión ha terminado.')
            action=body.get('action','sync')
            if action=='sync':
                peer=body.get('peer');name=body.get('name','Invitado')
                if not isinstance(peer,str) or not 1<=len(peer)<=100:raise ValueError('Participante inválido.')
                now=time.monotonic();self.peers={k:v for k,v in self.peers.items() if now-v['seen']<45}
                cursor=body.get('cursor');cursor={k:v for k,v in cursor.items() if k in ('lineNumber','column') and type(v) is int and 0<v<2000000} if isinstance(cursor,dict) else None
                self.peers[peer]={'id':peer,'name':str(name)[:80],'station':str(body.get('station','Navegador'))[:100],'path':str(body.get('path',''))[:300],'cursor':cursor,'seen':now}
                for path,value in body.get('updates',{}).items():
                    if path not in self.documents:raise PermissionError('El archivo no está compartido.')
                    doc=self.documents[path];previous=doc.get_update()
                    try:
                        doc.apply_update(decode(value))
                        if len(str(doc['text']).encode('utf-8'))>500000 or len(doc.get_update())>4000000:raise ValueError('El búfer compartido supera su presupuesto de memoria.')
                    except BaseException:
                        from pycrdt import Doc,Text
                        doc=Doc({'text':Text()},allow_multithreading=True);doc.apply_update(previous);self.documents[path]=doc;raise
                updates={path:encode(doc.get_update(decode(body['vectors'][path],100000) if body.get('vectors',{}).get(path) else None)) for path,doc in self.documents.items()}
                return {'room':self.id,'updates':updates,'paths':list(self.documents),'peers':[{k:v for k,v in peer.items() if k!='seen'} for peer in self.peers.values()],'allowRun':self.allow_run,'environment':self.environment(),'checkpoints':[{'id':c['id'],'label':c['label'],'created':c['created']} for c in self.checkpoints]}
            if action=='checkpoint':
                texts={p:str(d['text']) for p,d in self.documents.items()}
                if sum(len(t.encode('utf-8')) for t in texts.values())>2000000:raise ValueError('El punto de control admite hasta 2 MB de texto.')
                item={'id':secrets.token_hex(8),'label':str(body.get('label','Punto de equipo'))[:80],'created':time.time(),'texts':texts};self.checkpoints=(self.checkpoints+[item])[-4:]
                return {k:v for k,v in item.items() if k!='texts'}
            if action=='restore':
                if not owner:raise PermissionError('El anfitrión restaura los puntos de control compartidos.')
                item=next((c for c in self.checkpoints if c['id']==body.get('id')),None)
                if not item:raise ValueError('El punto de control ya no existe.')
                for path,text in item['texts'].items():
                    with self.documents[path].transaction():self.documents[path]['text'].clear();self.documents[path]['text'].insert(0,text)
                return {'restored':True}
            if action=='leave':self.peers.pop(body.get('peer'),None);return {'left':True}
            if action=='save':
                if not owner and not self.allow_run:raise PermissionError('El anfitrión guarda los cambios de esta sesión.')
                return self.save(body.get('path'))
            if action=='run':
                if not self.allow_run:raise PermissionError('El anfitrión no ha activado la ejecución compartida.')
                path=body.get('path');self.save(path);plan=self.features.runtimes.plan(self.workspace,path)
                if plan.get('preview'):raise ValueError('Usa una tarea de consola en esta sesión.')
                result=self.features.app.runner.start(plan['commands'],self.workspace.root,timeout=0);self.jobs.add(result['job']);return result
            if action in ('job','stop','input'):
                identity=body.get('job')
                if identity not in self.jobs:raise PermissionError('Esta ejecución no pertenece al equipo.')
                job=self.features.app.runner.jobs.get(identity)
                if job is None:raise ValueError('La ejecución ya no está disponible.')
                if action!='job' and not self.allow_run:raise PermissionError('Ejecución compartida desactivada.')
                if action=='stop':job.cancel();return {'stopped':True}
                if action=='input':job.write(str(body.get('text',''))[:65536]);return {'sent':True}
                offset=max(0,int(body.get('offset',0)));return {'output':job.output[offset:offset+50000],'offset':min(len(job.output),offset+50000),'done':job.done,'code':job.code,'queued':getattr(job,'queued',False)}
            raise ValueError('Acción de equipo desconocida.')

    def save(self,path):
        if path not in self.documents:raise PermissionError('El archivo no está compartido.')
        doc=self.documents[path];text=str(doc['text']);disk=self.workspace.read(path)
        if disk['revision']!=self.revisions[path]:
            if disk['content']!=text:raise ValueError('El archivo cambió fuera del equipo. Se conserva el búfer compartido; revisa ambos antes de guardar.')
        else:self.workspace.save(path,text,disk['revision'],newline=disk['newline'],bom=disk['bom'])
        result=self.workspace.read(path);self.revisions[path]=result['revision'];return {'saved':True,'path':path,'text':text,'revision':result['revision']}

    def environment(self):
        active=next((s for s in self.features.tern.sessions.values() if s.get('active') and s['workspace']==str(self.workspace.root)),None)
        return {'workspace':self.workspace.root.name,'host':socket.gethostname(),'runtime':'Lantern' if active else 'Proyecto','shared':True}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('La invitación no puede redirigir a otro servidor.')


class TeamService:
    def __init__(self,features):self.features=features;self.room=None;self.remote=None;self.thread=None;self.loop=None;self.server=None;self.url=None;self.tunnel=None;self.mode='local';self.internet_job=None
    def start(self,ws,body):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de compartirlo.')
        mode=body.get('mode','lan' if body.get('network') else 'local')
        if mode not in ('local','lan','internet'):raise ValueError('Selecciona este equipo, red local o Internet.')
        self.stop();self.mode=mode;self.room=TeamRoom(self.features,ws,body.get('documents',[]),body.get('allowRun',False));ready=threading.Event();errors=[]
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
        if name not in ('team.html','team-peer.js','team-peer.css') and not name.startswith(('vendor/monaco/','team-vendor/')):raise ValueError('Recurso no disponible.')
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
        result=self.contact(remote,{'action':'sync','peer':secrets.token_hex(12),'name':'Conectando','vectors':{}})
        self.stop();self.remote=remote;self.url=url;self.mode='internet' if parsed.scheme=='https' else 'local' if parsed.hostname in ('127.0.0.1','localhost','::1') else 'lan';return {**self.status(),'room':result['room']}

    def contact(self,remote,body):
        endpoint,token=remote;request=Request(endpoint,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=8) as response:
                raw=response.read(8000000)
                if len(raw)>=8000000:raise ValueError('Respuesta de equipo demasiado grande.')
                result=json.loads(raw)
        except HTTPError as error:
            try:message=json.loads(error.read(1000)).get('error')
            except Exception:message='No se pudo conectar con el equipo.'
            raise ValueError(message) from None
        if result.get('error'):raise ValueError(result['error'])
        return result

    def request(self,body):
        body={**body,'station':socket.gethostname()}
        if self.remote:return self.contact(self.remote,body)
        if not self.room:raise ValueError('No hay sesión de equipo.')
        result=self.room.request(body,owner=True)
        if body.get('action','sync')=='sync':result.update(connection=self.status()['connection'],invitation=self.status()['invitation'])
        return result
    def status(self):
        connection=self.tunnel.status() if self.tunnel else {'kind':self.mode,'phase':'ready' if self.room or self.remote else 'off','error':None}
        invitation=self.url
        if self.tunnel:invitation=connection['endpoint']+'/#'+self.room.token if connection['endpoint'] and self.room else None
        return {'active':bool(self.room or self.remote),'hosting':bool(self.room),'invitation':invitation,'room':self.room.id if self.room else None,'allowRun':bool(self.room and self.room.allow_run),'station':socket.gethostname(),'connection':connection}
    def connector(self,target):
        import hashlib
        name={'vscode':'zenit-team-0.1.0.vsix','jetbrains':'zenit-team-jetbrains-0.1.0.zip'}.get(target)
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
        self.room=None;self.remote=None;self.loop=None;self.server=None;self.thread=None;self.url=None
        return self.status()
