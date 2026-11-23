"""Opt-in extensions: each requested root and its dependencies share one host."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid
from .extensions import localized_manifest
from .runtime_paths import find_tool
from .terminals import child_environment, terminal_profiles
from .extension_lsp import PyreflyHost, JavaLanguageHost
from .preferences import atomic_json


class Host:
    def __init__(self, node, root, entry, workspace, options, services=None):
        self.lock=threading.Lock();self.write_lock=threading.Lock();self.pending={};self.dead_error=None;self.logs=''
        self.services=services;self.workspace=workspace;self.extension_id=options['extensionId'];self.extension_root=Path(root)
        self.extension_ids={self.extension_id,*[x['id'] for x in options.get('dependencies',[])]}
        from .extension_cancellation import ProviderOperations
        self.provider_operations=ProviderOperations(self)
        self.extension_roots=[self.extension_root,*[Path(x['root']) for x in options.get('dependencies',[])]]
        environment=child_environment()
        if self.extension_id=='nc-lang.nc-language' and services is not None:environment['ZENIT_NC_PROJECT_DIAGNOSTICS']='1'
        self.process=subprocess.Popen([node,str(Path(__file__).with_name('extension_host.cjs'))],cwd=workspace.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        threading.Thread(target=self.read,daemon=True).start();threading.Thread(target=self.read_errors,daemon=True).start()
        try:
            from .extension_bootstrap import activation_message
            with activation_message({'method':'activate','entry':str(entry),'root':str(root),'workspace':str(workspace.root),**options},options['storage']) as message:
                self.capabilities=self.request(message)
            from .extension_command_icons import command_icons
            icons={}
            for item in [*options.get('dependencies',[]),{'root':root,'manifest':options['manifest']}]:icons.update(command_icons(item['root'],item['manifest']))
            self.command_icons=icons
            for command in self.capabilities.get('commands',[]):
                if command['id'] in icons:command['icon']=icons[command['id']]
        except Exception as error:
            self.close();error.add_note(self.logs[-8000:]);raise

    def read(self):
        try:
            while line:=self.process.stdout.readline(2_000_001):
                if len(line)>2_000_000:self.close();break
                try:
                    message=json.loads(line)
                    if message.get('type')=='service':threading.Thread(target=self.service,args=(message,),daemon=True).start()
                    else:
                        with self.lock:waiter=self.pending.get(message.get('id'))
                        if waiter:waiter.put(message)
                except ValueError:pass
        except (OSError,ValueError):pass
        finally:
            with self.lock:
                self.dead_error='El proceso de la extensión terminó.'
                for waiter in self.pending.values():waiter.put({'error':self.dead_error})

    def read_errors(self):
        try:
            while data:=self.process.stderr.read1(4096):self.logs=(self.logs+data.decode('utf-8','replace'))[-12000:]
        except (OSError,ValueError):pass

    def send(self,message):
        raw=json.dumps(message,ensure_ascii=False).encode('utf-8')+b'\n'
        if len(raw)>2_000_000:raise ValueError('Mensaje de extensión demasiado grande.')
        with self.write_lock:self.process.stdin.write(raw);self.process.stdin.flush()

    def service(self,message):
        reply={'type':'serviceResult','id':message['id']}
        try:
            if self.services is None:raise ValueError('Servicios del IDE no conectados.')
            reply['result']=self.services.call(self,message['method'],message.get('params',{}))
        except Exception as error:reply['error']=str(error)
        try:self.send(reply)
        except (OSError,ValueError):pass

    def event(self,name,value):
        try:self.send({'type':'serviceEvent','name':name,'value':value})
        except (OSError,ValueError):pass

    def request(self, message, cancellation=None):
        message={**message,'id':uuid.uuid4().hex};waiter=queue.Queue()
        with self.lock:
            if self.dead_error:raise ValueError(self.dead_error)
            self.pending[message['id']]=waiter
        try:
            if cancellation:
                if not cancellation.send(message):return {'items':[],'cancelled':True}
            else:self.send(message)
            deadline=time.monotonic()+60
            while True:
                try:result=waiter.get(timeout=1);break
                except queue.Empty:
                    # A visible wizard is waiting for the human, not a hung command.
                    if self.services and self.services.has_interaction(self):deadline=time.monotonic()+60
                    if time.monotonic()>=deadline:self.close();raise ValueError('La extensión no respondió en 60 segundos. Se detuvo su proceso.')
            if result.get('error'):raise ValueError(result['error'])
            if result.get('id')!=message['id']:raise ValueError('Respuesta inesperada de la extensión.')
            return result['result']
        finally:
            with self.lock:self.pending.pop(message['id'],None)

    def close(self):
        if self.services:self.services.close_host(self)
        if self.process.poll() is None:
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(self.process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=5)
            else:self.process.kill()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill()
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            try:stream.close()
            except (OSError,ValueError):pass


class ExtensionRuntime:
    def __init__(self, store):
        self.store=store;self.hosts={};self.lock=threading.RLock();self.errors={};self.services=None
        self.approvals_path=store.root/'runtime-approvals.json'
        try:self.approvals=json.loads(self.approvals_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.approvals={}
        if not isinstance(self.approvals,dict):self.approvals={}
        self.graph_approvals_path=store.root/'runtime-dependency-approvals.json'
        try:self.graph_approvals=json.loads(self.graph_approvals_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.graph_approvals={}
        if not isinstance(self.graph_approvals,dict):self.graph_approvals={}
        self.graph_approvals={key:value for key,value in self.graph_approvals.items() if isinstance(value,dict)}
    def snapshot(self):
        with self.lock:return {'hosts':[{'id':key,'running':host.process.poll() is None,**host.capabilities,'logs':host.logs} for key,host in self.hosts.items()],'errors':dict(self.errors)}
    def graph_signature(self,graph):
        """Pin the reviewed package versions and required dependency edges."""
        import hashlib
        records=[{'id':item['id'].casefold(),'sha256':self.store.installed[item['id']].get('sha256'),
                  'version':item['manifest'].get('version'),'requires':item['manifest'].get('extensionDependencies',[])} for item in graph]
        return hashlib.sha256(json.dumps(records,sort_keys=True).encode('utf-8')).hexdigest()
    def approve(self,workspace,eid,graph):
        key=str(workspace.root);self.approvals[key]=list(set(self.approvals.get(key,[]))|{eid});atomic_json(self.approvals_path,self.approvals);self.errors.pop(eid,None)
        self.graph_approvals.setdefault(key,{})[eid]=self.graph_signature(graph)
        atomic_json(self.graph_approvals_path,self.graph_approvals)
    def restore(self,workspace):
        if not workspace.trusted:return self.snapshot()
        with self.lock:
            for eid in self.approvals.get(str(workspace.root),[]):
                if eid in self.hosts or eid in self.errors:continue
                if not self.store.installed.get(eid,{}).get('enabled'):continue
                try:
                    from .extension_dependencies import dependency_graph
                    graph=dependency_graph(self.store,eid)
                    approved=self.graph_approvals.get(str(workspace.root),{}).get(eid)
                    # Legacy single-package approvals can migrate. A newly added
                    # executable dependency needs review instead of silent execution.
                    if (approved and approved!=self.graph_signature(graph)) or (not approved and len(graph)>1):
                        raise ValueError('El paquete o sus dependencias cambiaron. Revisa e inicia su motor para autorizar esta versión.')
                    self.start(workspace,eid,True)
                except Exception as error:self.errors[eid]=str(error)
        return self.snapshot()

    def migrate_factory_approvals(self,updates):
        """An app-shipped exact-digest update can retain an existing single-package approval.

        New dependencies, custom packages and projects without prior approval keep
        the normal review path. The factory catalog is part of the app payload.
        """
        from .extension_dependencies import dependency_graph
        import hashlib
        changed=False
        with self.lock:
            for item in updates:
                previous=item.get('_factoryPrevious');eid=item['id']
                if not previous or not item.get('enabled'):continue
                try:graph=dependency_graph(self.store,eid)
                except ValueError:continue
                if len(graph)!=1 or graph[0]['manifest'].get('extensionDependencies'):continue
                old=[{'id':eid.casefold(),'sha256':previous['sha256'],'version':previous['version'],'requires':[]}]
                signature=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()
                for workspace,entries in self.graph_approvals.items():
                    if eid in self.approvals.get(workspace,[]) and entries.get(eid)==signature:
                        entries[eid]=self.graph_signature(graph);changed=True
            if changed:atomic_json(self.graph_approvals_path,self.graph_approvals)
    def start(self, workspace, eid, consent):
        if consent is not True or not workspace.trusted:raise PermissionError('Autoriza la extensión ejecutable en un proyecto de confianza.')
        with self.lock:
            from .extension_dependencies import dependency_graph
            graph=dependency_graph(self.store,eid)
            eid=graph[-1]['id']
            info=self.store.installed.get(eid)
            if not info or not info.get('enabled'):raise ValueError('Activa primero la extensión instalada.')
            root=(self.store.root/info['directory']/'extension').resolve();manifest=localized_manifest(root,self.store.prefs.get('general.locale'))
            if eid.lower()=='meta.pyrefly':
                self.stop(eid);self.hosts[eid]=PyreflyHost(root,workspace)
                self.approve(workspace,eid,graph)
                self.store.prefs.audit('extension.execute',extension=eid,engine='native-lsp')
                return self.snapshot()
            if eid.lower()=='redhat.java':
                self.stop(eid);self.hosts[eid]=JavaLanguageHost(root,workspace,self.store.root/'.runtime-data'/eid)
                self.approve(workspace,eid,graph)
                return self.snapshot()
            entry=(root/manifest.get('lumen',{}).get('main',manifest.get('main',''))).resolve()
            if entry.suffix not in ('.js','.cjs','.mjs') and entry.with_suffix('.js').is_file():entry=entry.with_suffix('.js')
            if not entry.is_relative_to(root) or not entry.is_file() or entry.suffix not in ('.js','.cjs','.mjs'):raise ValueError('La extensión necesita un main Node.js compatible con la API preview.')
            node=find_tool('node')
            if not node:raise ValueError('Instala Node.js para ejecutar extensiones.')
            extensions=[]
            for item in self.store.list():
                other=self.store.root/item['directory']/'extension'
                try:extensions.append({'id':item['id'],'root':str(other),'manifest':localized_manifest(other,self.store.prefs.get('general.locale'))})
                except (OSError,ValueError):pass
            profiles=terminal_profiles()
            preferred=self.store.prefs.get('terminal.defaultProfile')
            profiles=sorted(profiles,key=lambda row:row['id']!=preferred)
            options={'installedAt':self.store.prefs.directory.stat().st_ctime*1000,'extensionId':eid,'manifest':manifest,'extensions':extensions,'dependencies':graph[:-1],'storage':str(self.store.root/'.runtime-data'/eid),'locale':self.store.prefs.get('general.locale'),'shell':profiles[0]['argv'][0] if profiles else None,'editorState':self.services.editor_snapshot if self.services else None,'iconTheme':self.services.icon_state()['configurationId'] if self.services else 'zenit','themeKind':self.services.theme_state()['kind'] if self.services else 1,'themeLabel':self.services.theme_state()['label'] if self.services else 'Zénit Día'}
            options['authenticationProviders']=['github'] if self.services and hasattr(self.services.platform,'extension_accounts') else []
            if manifest.get('contributes',{}).get('notebookRenderer') and self.services:
                from .foundation import python_command
                options['notebookPython']=python_command(workspace,self.services.platform.runtimes.config.get('tools'))
            self.stop(eid);self.hosts[eid]=Host(node,root,entry,workspace,options,self.services)
            self.approve(workspace,eid,graph)
            self.store.prefs.audit('extension.execute',extension=eid)
        return self.snapshot()
    def request(self, workspace, body):
        if not workspace.trusted:raise PermissionError('Proyecto no autorizado.')
        host=self.hosts.get(body.get('id'))
        if not host:raise ValueError('Inicia el motor de la extensión primero.')
        method=body.get('method')
        if isinstance(host,Host) and method in ('provide','resolveCompletion','resolveAction'):
            with host.provider_operations.begin(body.get('requestKey')) as operation:
                if operation.event.is_set():return {'items':[],'cancelled':True}
                try:result=self._request(workspace,host,body,operation)
                except Exception:
                    if not operation.event.is_set():raise
                    return {'items':[],'cancelled':True}
                return {'items':[],'cancelled':True} if operation.event.is_set() else result
        return self._request(workspace,host,body)

    def cancel(self,workspace,body):
        if not workspace.trusted:raise PermissionError('Proyecto no autorizado.')
        host=self.hosts.get(body.get('id'))
        if not isinstance(host,Host):return {'cancelled':False}
        host.provider_operations.cancel(body.get('requestKey'));return {'cancelled':True}

    def _request(self,workspace,host,body,operation=None):
        method=body.get('method')
        if host.extension_id=='nc-lang.nc-language' and isinstance(host,Host) and method=='provide' and body.get('kind')=='rename':
            from .nc_refactor import rename
            result=rename(self.services.platform,workspace,host,body,operation.event.is_set if operation else lambda:False) if self.services else None
            if result is not None:return result
        if method not in ('command','provide','virtual','willSave','didSave','tree','resolveAction','resolveCompletion','decorations','webviewMessage','webviewDispose','ports','debugVisualization','treeCheckbox','editSessionIdentity','terminalLinks','terminalLink','tasks','notebook'):raise ValueError('Operación no válida.')
        if method=='notebook':
            from .extension_services import file_path
            target=file_path(body.get('uri'))
            if not target.resolve().is_relative_to(workspace.root.resolve()):raise ValueError('Abre un cuaderno dentro del proyecto actual.')
        if method=='decorations':
            paths=body.get('paths')
            if not isinstance(paths,list) or len(paths)>300:raise ValueError('Lista de decoraciones no válida.')
            for path in paths:
                if not isinstance(path,str):raise ValueError('Ruta de decoración no válida.')
                workspace.resolve(path,must_exist=False)
        document=body.get('document',{})
        if document.get('path'):
            candidate=Path(document['path'])
            if candidate.is_absolute():
                from .extension_services import file_path
                file_path(str(candidate))
            else:workspace.resolve(document['path'],must_exist=False)
        message={k:body[k] for k in ('method','command','kind','document','position','range','uri','arguments','reason','newName','view','element','context','options','character','positions','color','action','completion','name','index','text','controller','paths','revision','panel','message','ports','visualization','checkboxState','scheme','identity1','identity2','line','terminal','link') if k in body}
        if self.services and host.extension_id=='nc-lang.nc-language' and method=='provide':
            pending=(self.services.platform.workbenches.snapshot(workspace).get('session') or {}).get('documents',[])
            message['documents']=[{'path':d['path'],'text':d['content'],'language':'nc'} for d in pending
                                  if d.get('dirty') and isinstance(d.get('content'),str) and not Path(d['path']).is_absolute()
                                  and Path(d['path']).suffix.lower() in ('.n','.nc') and d['path']!=document.get('path')]
        return host.request(message,cancellation=operation) if operation else host.request(message)
    def stop(self,eid,forget=False):
        with self.lock:
            if forget:
                for key,ids in self.approvals.items():self.approvals[key]=[x for x in ids if x!=eid]
                atomic_json(self.approvals_path,self.approvals)
                for entries in self.graph_approvals.values():entries.pop(eid,None)
                atomic_json(self.graph_approvals_path,self.graph_approvals)
            self.errors.pop(eid,None)
            host=self.hosts.pop(eid,None)
            if host:host.close()
        return self.snapshot()
    def invalidate(self,eids,reason='Una dependencia cambió; revisa e inicia de nuevo el motor.'):
        changed={value.casefold() for value in eids if isinstance(value,str)}
        with self.lock:
            for key,host in list(self.hosts.items()):
                members={key.casefold(),*[value.casefold() for value in host.capabilities.get('dependencies',[])]}
                if changed & members:
                    self.stop(key)
                    self.errors[key]=reason
        return self.snapshot()
    def shutdown(self):
        for eid in list(self.hosts):self.stop(eid)
