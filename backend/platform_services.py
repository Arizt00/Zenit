"""Authenticated platform routes, composed without changing legacy API contracts."""
from __future__ import annotations
import json
import os
import threading
import time
from .preferences import Preferences
from .extensions import ExtensionStore
from .terminals import TerminalManager
from .hardware import HardwareMonitor
from .toolchains import Toolchains
from .lsp import LanguageServers
from .providers import AIRouter
from .studio import StudioState
from .debug_manager import DebugManager
from .runtimes import Runtimes
from .preview import WebPreview
from .lantern import Lantern
from .diagnostics import inspect_buffer, output_diagnostics
from .downloads import Downloads
from .extension_runtime import ExtensionRuntime
from .hacker import Hacker
from .updates import Updates
from .buffers import Buffers
from .extension_services import ExtensionServices,file_path
from .version import VERSION, REVISION
from .simulation import Simulation
from .machines import Machines
from .melody_files import MelodyFiles
from .melody_voice import MelodyVoice
from .permissions import WorkspacePermissions
from .hilo import Hilo, Connections
from .tern import Tern
from .team import TeamService
from .binary_tools import BinaryTools
from .workbenches import Workbenches
from .execution_targets import ExecutionTargets
from .sdk_manager import SDKManager


class PlatformServices:
    def __init__(self,app,directory=None):
        self.app=app;self.prefs=Preferences(directory);self.extensions=ExtensionStore(self.prefs)
        self.permissions=WorkspacePermissions(self.prefs.directory)
        self.terminals=TerminalManager(self.prefs,app.project);self.tools=Toolchains(self.prefs,app.runner)
        self.lsp=LanguageServers(self.prefs,self.tools);self.ai=AIRouter(self.prefs);self.hardware=HardwareMonitor(self.prefs)
        self.command_seq=0;self.command_events=[];self.command_lock=threading.Lock()
        self.studio=StudioState(self.prefs.directory)
        self.runtimes=Runtimes(self.prefs);self.preview=WebPreview();self.debugger=DebugManager(self.runtimes,app.runner)
        self.lantern=Lantern(self.runtimes,app.runner,self.preview)
        self.downloads=Downloads(self.prefs.directory);self.extension_runtime=ExtensionRuntime(self.extensions)
        self.hacker=Hacker(self);self.updates=Updates(self.prefs,self.downloads)
        self.simulation=Simulation(self);self.machines=Machines(self)
        self.buffers=Buffers()
        self.extension_services=ExtensionServices(self);self.extension_runtime.services=self.extension_services
        from .extension_accounts import ExtensionAccounts
        self.extension_accounts=ExtensionAccounts(self.prefs,self._accounts_changed)
        self.melody_files=MelodyFiles(self)
        from .project_tests import ProjectTests
        self.tests=ProjectTests(self)
        from .git_conflicts import GitConflicts
        self.conflicts=GitConflicts(self)
        self.voice=MelodyVoice(self.prefs)
        from .python_packages import PythonPackages
        self.python_packages=PythonPackages(self)
        from .native_packages import NativePackages
        self.native_packages=NativePackages(self)
        self.hilo=Hilo(self);self.connections=Connections(self);self.tern=Tern(self)
        self.team=TeamService(self);self.binary_tools=BinaryTools(self)
        self.workbenches=Workbenches(self);self.execution=ExecutionTargets(self);self.sdk=SDKManager(self)
        self.runtimes.execution=self.execution
        self._register_subsystems()
    def _accounts_changed(self):
        self.extension_services.emit('authentication.changed',provider='github')
        for host in list(self.extension_runtime.hosts.values()):
            if hasattr(host,'event'):host.event('authentication.changed',{'provider':'github'})
    def _register_subsystems(self):
        core=self.hilo
        core.register('runner',self.app.runner,workspace_stop=self._stop_jobs,shutdown=self.app.runner.shutdown)
        core.register('workbench',self.workbenches)
        core.register('sdk',self.sdk,depends=('runner',))
        core.register('runtimes',self.runtimes,depends=('sdk',))
        core.register('execution',self.execution,depends=('runtimes','workbench'))
        core.register('hacker',self.hacker,depends=('execution',),shutdown=self.hacker.shutdown)
        core.register('buffers',self.buffers,workspace_stop=lambda ws:self.buffers.clear())
        core.register('terminals',self.terminals,depends=('hacker',),workspace_stop=lambda ws:self.terminals.shutdown(),shutdown=self.terminals.shutdown)
        core.register('lsp',self.lsp,depends=('runtimes',),workspace_stop=lambda ws:self.lsp.shutdown(),shutdown=lambda:self.lsp.shutdown(permanent=True))
        core.register('preview',self.preview,depends=('runtimes',),workspace_stop=lambda ws:self.preview.stop(),shutdown=self.preview.stop)
        core.register('debug',self.debugger,depends=('runtimes','terminals'),workspace_stop=lambda ws:self.debugger.stop(),shutdown=self.debugger.stop)
        core.register('lantern',self.lantern,depends=('preview','runner'),workspace_stop=lambda ws:self.lantern.stop(),shutdown=self.lantern.stop)
        core.register('machines',self.machines,depends=('terminals',))
        core.register('environments',self.tern,depends=('machines','lantern'),workspace_stop=self.tern.close_workspace,shutdown=lambda:self.tern.close_workspace(self.app.workspace))
        core.register('melody',self.ai,depends=('runtimes',),workspace_stop=self._stop_ai,shutdown=self.ai.shutdown)
        core.register('voice',self.voice,depends=('melody',),workspace_stop=lambda ws:self.voice.stop(),shutdown=self.voice.shutdown)
        core.register('extensions',self.extensions,depends=('sdk',),shutdown=self.extensions.shutdown)
        core.register('extension-runtime',self.extension_runtime,depends=('extensions','lsp','buffers'),workspace_stop=lambda ws:self.extension_runtime.shutdown(),shutdown=self.extension_runtime.shutdown)
        core.register('downloads',self.downloads,shutdown=self.downloads.shutdown)
        core.register('updates',self.updates,depends=('downloads',),shutdown=self.updates.shutdown)
        core.register('team',self.team,depends=('buffers','environments','execution'),workspace_stop=lambda ws:self.team.stop(),shutdown=self.team.stop)
        core.subscribe('sdk.changed',lambda event:self.lsp.shutdown())
    def _stop_jobs(self,ws):
        for job in list(self.app.runner.jobs.values()):
            if not job.done and job.cwd.is_relative_to(ws.root):job.cancel()
    def _stop_ai(self,ws):
        for job in list(self.ai.jobs.values()):
            if not job.done:job.cancel()
        self.ai.clear_history()
    def restore_trust(self):
        state=self.permissions.state(self.app.workspace.root,direct=not self.prefs.get('security.confirmRoutineActions'))
        self.app.workspace.trusted=state['trusted'];return state
    def trust(self,value):
        self.permissions.set(self.app.workspace.root,value);self.app.workspace.trusted=value
        if not value:self.workspace_changed()
        state=self.permissions.state(self.app.workspace.root)
        self.extension_services.emit('zenit.trust.changed',**state);return state
    def state(self):
        web=self.app.project/'web/vendor'
        return {'version':VERSION,'revision':REVISION,'preferences':self.prefs.export(),'providers':self.ai.vault.state(),
                'xterm':(web/'xterm/xterm.js').is_file() and (web/'xterm-fit/addon-fit.js').is_file(),
                'installedExtensions':len(self.extensions.installed),'dataDirectory':str(self.prefs.directory),
                'development':self.hilo.cached('language-servers',self.tools.discover_servers),'commandSequence':self.command_seq}
    def _trusted(self):
        if not self.app.workspace.trusted:raise PermissionError('El proyecto no es de confianza. Autorízalo antes de continuar.')
    def execution_workspace(self,ws,path):
        """An exterior file must already be part of the user's open session."""
        from pathlib import Path
        if not isinstance(path,str):raise ValueError('Ruta de ejecución inválida.')
        if not Path(path).is_absolute():return ws,path
        self._trusted();target=Path(path).resolve()
        known={os.path.normcase(str(Path(b['path']).resolve())) for b in self.buffers.snapshot()['buffers'] if Path(b['path']).is_absolute()}
        if os.path.normcase(str(target)) not in known or not target.is_file():raise PermissionError('Abre este archivo en la sesión antes de ejecutarlo.')
        from .workspace import Workspace
        scoped=Workspace(target.parent,ws.native);scoped.trusted=True
        return scoped,target.name
    def _terminal(self,sid):
        session=self.terminals.get(sid)
        if session.profile.get('kind')!='account':self._trusted()
        return session
    def get(self,path,query):
        q=lambda key,default='':query.get(key,[default])[0]
        if path=='/state':return self.state()
        if path=='/workbench':return self.workbenches.snapshot(self.app.workspace)
        if path=='/execution/targets':return self.execution.inventory(self.app.workspace,q('refresh')=='1')
        if path=='/sdk':return self.sdk.status()
        if path=='/operations':return self.hilo.snapshot(self.app.workspace.root)
        if path=='/testing':return {**self.tests.discover(self.app.workspace),**self.tests.snapshot(self.app.workspace,q('run'))}
        if path=='/git/conflicts':return self.conflicts.snapshot(self.app.workspace)
        if path=='/git/conflict':self._trusted();return self.conflicts.read(self.app.workspace,q('path'))
        if path=='/testing/plan':return self.tests.plan(self.app.workspace,{'framework':q('framework','unittest'),'selection':q('selection'),'coverage':q('coverage')=='1','build':q('build')=='1'})
        if path=='/testing/coverage':self._trusted();return self.tests.coverage(self.app.workspace,q('run'))
        if path=='/ai/files/trace':self._trusted();return self.melody_files.trace(self.app.workspace,q('receipt'))
        if path=='/operations/resources':self._trusted();return self.hilo.resources(self.app.workspace.root)
        if path=='/connections':return {'connections':self.connections.inventory()}
        if path=='/accounts/extensions':return self.extension_accounts.snapshot()
        if path=='/binary/info':return self.binary_tools.info(q('path'))
        if path=='/team':return self.team.status()
        if path=='/team/connector':return self.team.connector(query.get('target',['vscode'])[0])
        if path=='/hilo':return self.hilo.snapshot(self.app.workspace.root)
        if path=='/hilo/connections':return {'connections':self.connections.inventory()}
        if path=='/lantern/environments':return self.tern.snapshot(self.app.workspace)
        if path=='/lantern/environments/inspect':self._trusted();return self.tern.portability.inspect(self.app.workspace,q('file'))
        if path=='/python/packages':return self.python_packages.status(self.app.workspace)
        if path=='/ai/memory':
            key=self.ai.memory.key(str(self.app.workspace.root),q('path'),q('provider'))
            data,_=self.ai.memory.read(key)
            return {'turns':len(data['turns']),'updated':data.get('updated'),'path':q('path')}
        if path=='/native/packages':return self.native_packages.status(self.app.workspace)
        if path=='/foundation':
            from .foundation import status
            return status()
        if path=='/simulation':return self.simulation.status()
        if path=='/machines':return self.machines.snapshot()
        if path=='/hacker':return self.hacker.tools()
        if path=='/updates':return self.updates.snapshot()
        if path=='/buffers':return self.buffers.snapshot()
        if path=='/buffers/document':return self.buffers.document(self.app.workspace,q('path'))
        if path=='/settings':return self.prefs.describe()
        if path=='/studio':return self.studio.export()
        if path=='/debug':return self.debugger.snapshot()
        if path=='/lantern':return self.lantern.snapshot()
        if path=='/lantern/template':return self.lantern.template(q('language'))
        if path=='/downloads':return self.downloads.snapshot()
        if path=='/extensions/runtime':return self.extension_runtime.snapshot()
        if path=='/extensions/dependencies':
            from .extension_dependencies import dependency_graph
            return {'extensions':[{'id':x['id'],'executable':bool(x['manifest'].get('main') or x['manifest'].get('lumen',{}).get('main'))} for x in dependency_graph(self.extensions,q('id'))]}
        if path=='/extensions/services':return self.extension_services.snapshot()
        if path=='/extensions/output':self._trusted();return self.extension_services.output(q('extension'),q('key'))
        if path=='/extensions/resource':return self.extension_services.resource(q('panel'),q('path'))
        if path=='/extensions/file':
            self._trusted();p=file_path(q('path'));item=self.extension_services.file_workspace(p).open_file(p.name);item.update(path=self.extension_services.key(self.app.workspace,p),name=p.name,external=not p.is_relative_to(self.app.workspace.root));return item
        if path=='/extensions/binary':
            self._trusted();p=file_path(q('path'));item=self.extension_services.file_workspace(p).binary(p.name,int(q('offset','0')),int(q('count','512')));item['path']=self.extension_services.key(self.app.workspace,p);return item
        if path=='/extensions/review':return self.extensions.review_status(q('id'))
        if path=='/extensions/updates':return self.extensions.updates()
        if path=='/languages':return self.runtimes.status()
        if path=='/extensions':return {'extensions':self.extensions.list()}
        if path=='/extensions/search':return self.extensions.search(q('q'),int(q('offset','0')))
        if path=='/extensions/icon':return self.extensions.catalog_icon(q('url'))
        if path=='/extensions/contributions':
            stamp=self.extensions.index.stat().st_mtime_ns if self.extensions.index.exists() else 0
            key=f'contributions:{stamp}:{self.prefs.get("general.locale")}:{self.prefs.get("extensions.loadContributions")}'
            return self.hilo.cached(key,self.extensions.contributions,ttl=30)
        if path=='/terminals/profiles':return self.terminals.profiles()
        if path=='/terminals':return {'sessions':self.terminals.list()}
        if path=='/terminals/read':return self._terminal(q('id')).read(int(q('offset','0')))
        if path=='/tools':return self.tools.detect(q('refresh')=='1')
        if path=='/hardware':return self.hardware.sample()
        if path=='/ai/providers':return {'providers':self.ai.vault.state()}
        if path=='/ai/voice':return self.voice.status()
        if path=='/ai/voice/job':return self.voice.snapshot(q('id'))
        if path=='/ai/account':return self.ai.accounts.status(q('provider'))
        if path=='/ai/job':return self.ai.get(q('id')).state(int(q('offset','0')))
        if path=='/lsp/events':self._trusted();return self.lsp.poll(q('id'),int(q('after','0')))
        if path=='/ui/events':
            after=int(q('after','0'))
            with self.command_lock:return {'events':[x for x in self.command_events if x['seq']>after],'sequence':self.command_seq}
        if path=='/audit':
            p=self.prefs.directory/'audit.jsonl'
            return {'lines':p.read_text(encoding='utf-8').splitlines()[-150:] if p.exists() else []}
        raise FileNotFoundError('Ruta de plataforma desconocida.')
    def post(self,path,body):
        ws=self.app.workspace
        if path=='/binary/save':return self.binary_tools.save(body)
        if path=='/binary/build':return self.binary_tools.build(body)
        if path=='/binary/finish':return self.binary_tools.finish(body)
        if path=='/team/start':return self.team.start(ws,body)
        if path=='/team/join':return self.team.join(ws,body.get('invitation',''))
        if path=='/team/stop':return self.team.stop()
        if path=='/team/internet':self._trusted();return self.team.internet()
        if path=='/team/request':
            self._trusted();return self.team.request(body)
        if path=='/extensions/uri':
            self._trusted();uri=body.get('uri','');from urllib.parse import urlsplit
            parsed=urlsplit(uri)
            if parsed.scheme!='lumen' or parsed.netloc not in self.extension_runtime.hosts:raise ValueError('No hay un controlador activo para este enlace.')
            self.extension_runtime.hosts[parsed.netloc].event('uri',{'uri':uri});return {'delivered':True}
        if path=='/workbench/session':return self.workbenches.checkpoint(ws,body)
        if path=='/workbench/discard':return self.workbenches.discard(ws,body.get('path'))
        if path=='/workbench/spaces/save':return self.workbenches.save_space(ws,body)
        if path=='/workbench/spaces/delete':return self.workbenches.delete_space(ws,body.get('name'))
        if path=='/execution/select':return self.execution.select(ws,body)
        if path=='/sdk/activate':self._trusted();return self.sdk.activate(body.get('directory'))
        if path=='/testing/run':return self.tests.start(ws,body)
        if path=='/git/conflicts/resolve':return self.conflicts.apply(ws,body)
        if path=='/git/conflicts/draft':return self.conflicts.draft(ws,body)
        if path=='/testing/cancel':return self.tests.cancel(ws,body.get('run'))
        if path=='/accounts/extensions/connect':return self.extension_accounts.connect(body)
        if path=='/accounts/extensions/disconnect':return self.extension_accounts.disconnect()
        if path=='/sdk/deactivate':self._trusted();return self.sdk.deactivate(body.get('directory'))
        if path=='/sdk/import':
            self._trusted();return self.hilo.submit('Preparar SDK',lambda event:self.sdk.install(body.get('path'),event),workspace=ws.root,key='sdk-install')
        if path in ('/hilo/refresh','/connections/refresh'):self.hilo.invalidate();return {'connections':self.connections.inventory()}
        if path=='/hilo/clear':return self.hilo.clear_finished(ws.root)
        if path in ('/hilo/cancel','/operations/cancel'):
            self._trusted()
            job=next((j for j in self.hilo.snapshot(ws.root)['jobs'] if j['id']==body.get('id')),None)
            if not job:raise ValueError('Task is not in this workspace.')
            return self.hilo.cancel(body['id'])
        if path=='/operations/priority':
            self._trusted()
            if not any(j['id']==body.get('id') for j in self.hilo.snapshot(ws.root)['jobs']):raise ValueError('La tarea no pertenece a este proyecto.')
            return self.hilo.prioritize(body['id'],body.get('priority'))
        if path=='/operations/clear':return self.hilo.clear_finished(ws.root)
        if path in ('/hilo/connect','/connections/open'):return self.connections.launch(ws,body)
        if path=='/machines/base':self._trusted();return self.machines.configure_base(body.get('directory'))
        if path.startswith('/lantern/environments/'):
            self._trusted();action=path.rsplit('/',1)[-1]
            if action=='create':return self.hilo.submit('Lantern · create environment',lambda event:self.tern.create(ws,body,event),workspace=ws.root,key='tern-create:'+str(ws.root))
            if action=='restore':return self.tern.reopen(ws,body.get('file',''))
            if action=='save':return self.tern.save(ws,body.get('id'),body.get('file'))
            if action in ('export','rebuild'):
                return self.hilo.submit('Lantern · '+action,lambda event:getattr(self.tern.portability,action)(ws,body,event),workspace=ws.root,key='tern-portable:'+str(ws.root))
            if action=='activate':return self.tern.activate(ws,body.get('id'))
            if action in ('console','stop'):
                return self.hilo.submit('Lantern · '+action,lambda event:getattr(self.tern,action)(ws,body.get('id')),workspace=ws.root,key='tern:'+str(body.get('id')),priority=0)
            raise ValueError('Unknown environment action.')
        if path=='/python/packages':return self.python_packages.start(ws,body)
        if path=='/native/packages':return self.native_packages.start(ws,body)
        if path=='/native/packages/cancel':return self.native_packages.cancel(ws)
        if path=='/python/packages/cancel':return self.python_packages.cancel(ws)
        if path=='/ai/voice/start':return self.voice.start(body.get('text'))
        if path=='/ai/voice/cancel':return self.voice.cancel(body.get('id'))
        if path=='/simulation/run':return self.simulation.run(ws,body)
        if path=='/foundation/action':
            from .foundation_actions import action
            return action(self,ws,body)
        if path=='/machines/create':
            self._trusted()
            return self.machines.create_arch() if body.get('type')=='arch' and not body.get('host') else self.machines.save_ssh(body)
        if path=='/machines/start':return self.machines.start(ws,body.get('id'))
        if path=='/machines/stop':
            self._trusted();return self.machines.stop(body.get('id'))
        if path=='/buffers':return self.buffers.update(ws,body)
        if path=='/extensions/applyEdit':return self.extension_services.workspace_edit(ws,body['edit'],body.get('documents'))
        if path=='/extensions/pick':self._trusted();return self.extension_services.answer_prompt(body['id'],body.get('value'))
        if path=='/extensions/quickinput/event':self._trusted();return self.extension_services.quickinput_event(body)
        if path=='/extensions/output/control':self._trusted();return self.extension_services.output(body.get('extension'),body.get('key'),body.get('action'),body.get('level'))
        if path=='/extensions/webview/document':self._trusted();return self.extension_services.webview_document(body['panel'],body['html'])
        if path=='/extensions/save':
            self._trusted();p=file_path(body['path']);item=self.extension_services.file_workspace(p).save(p.name,body['content'],body.get('revision'),newline=body.get('newline','LF'),bom=body.get('bom',False));item.update(path=str(p),saved=True);return item
        if path=='/hacker/start':return self.hacker.start(ws,body.get('path',''),body.get('content'),body.get('mode'),body.get('args'))
        if path=='/hacker/attach':return self.hacker.attach(ws,body.get('job'))
        if path=='/updates/check':return self.updates.check(body.get('download') is True)
        if path=='/updates/download':return self.updates.download()
        if path=='/files/operation':
            from .file_actions import perform
            result=perform(ws,body);self.extension_services.emit('zenit.tree.changed');return result
        if path=='/downloads/start':return self.downloads.start(body.get('url',''),body.get('name',''),body.get('sha256',''))
        if path=='/downloads/pause':return self.downloads.pause(body.get('id'))
        if path=='/downloads/resume':return self.downloads.resume(body.get('id'))
        if path=='/extensions/runtime/start':return self.extension_runtime.start(ws,body.get('id'),body.get('consent'))
        if path=='/extensions/runtime/stop':return self.extension_runtime.stop(body.get('id'),forget=True)
        if path=='/extensions/runtime/restore':return self.extension_runtime.restore(ws)
        if path=='/extensions/runtime/request':return self.extension_runtime.request(ws,body)
        if path=='/lantern/start':
            self.execution.require_local(ws,'Los checkpoints y la ejecución continua de Lantern')
            if self.debugger.snapshot()['status'] in ('running','paused'):self.debugger.stop()
            return self.lantern.start(ws,body.get('path',''),body.get('content'),body.get('version'))
        if path=='/lantern/buffer':return self.lantern.buffer(ws,body.get('path',''),body.get('content'),body.get('version'))
        if path=='/lantern/stop':return self.lantern.stop()
        if path=='/lantern/restart':self._trusted();return self.lantern.restart()
        if path=='/diagnostics':return inspect_buffer(ws,self.runtimes,body.get('path',''),body.get('content',''))
        if path=='/diagnostics/check':
            if not ws.trusted:return {'skipped':'workspace-trust'}
            if self.lantern.snapshot()['active']:return {'skipped':'lantern'}
            plan=self.runtimes.plan(ws,body.get('path',''),check=True)
            return self.app.runner.start(plan['commands'],ws.root,timeout=20) if plan['commands'] else {'output':''}
        if path=='/diagnostics/output':return {'diagnostics':output_diagnostics(str(body.get('output',''))[:512000],str(body.get('path','')))}
        if path=='/studio':
            result=self.studio.update(body)
            if any(key in body for key in ('displayName','avatar','workspaceStyle')):self.extension_services.emit('zenit.studio.changed')
            return result
        if path=='/languages/config':return self.runtimes.save(body)
        if path=='/preview':return self.preview.start(ws,body.get('path',''),body.get('buffers'))
        if path=='/debug/start':
            self.execution.require_local(ws,'La depuración DAP')
            self.lantern.stop()
            return self.debugger.start(ws,body.get('path',''),body.get('breakpoints',[]))
        if path=='/debug/command':self._trusted();return self.debugger.command(body.get('command'))
        if path=='/debug/input':self._trusted();return self.debugger.input(body.get('text'))
        if path=='/debug/machine':self._trusted();return self.debugger.machine(body)
        if path=='/melody/research':
            from .melody_lab import research
            return research(ws,body)
        if path=='/settings':
            result=self.prefs.update(body.get('settings',{}),body.get('reset') is True)
            if body.get('reset') is True or 'security.confirmRoutineActions' in body.get('settings',{}):
                state=self.restore_trust()
                if not state['trusted']:self.workspace_changed()
                self.extension_services.emit('zenit.trust.changed',**state)
            if body.get('reset') is True or any(key.startswith(('appearance.','editor.','terminal.','security.')) or key in ('general.locale','extensions.loadContributions') for key in body.get('settings',{})):
                self.extension_services.theme_changed();self.extension_services.icons_changed()
                self.extension_services.emit('zenit.preferences.changed')
            if not self.prefs.get('security.terminals'):self.terminals.shutdown()
            if not self.prefs.get('security.cloudAI'):
                for j in list(self.ai.jobs.values()):
                    if not j.done and j.provider not in ('ollama','emma'):j.cancel()
            return result
        if path=='/extensions/inspect':
            return self.extensions.inspect_local(body['path']) if 'path' in body else self.extensions.inspect_remote(body.get('id',''),body.get('version','latest'))
        if path=='/extensions/editor-state':return self.extension_services.editor_state(ws,body)
        if path=='/extensions/review/start':return self.extensions.start_review(body)
        if path=='/extensions/review/cancel':return self.extensions.review_status(body.get('id'),cancel=True)
        if path=='/extensions/install':
            if body.get('plan'):
                result=self.extensions.install_plan(body['plan'],body.get('consent'))
                self.extension_runtime.invalidate([x['id'] for x in result['installed']])
                self.extension_services.theme_changed();self.extension_services.icons_changed();self.extension_services.emit('zenit.contributions.changed')
                return result
            result=self.extensions.install(body.get('ticket',''),body.get('consent'))
            self.extension_runtime.invalidate([result['id']]);self.extension_services.theme_changed();self.extension_services.icons_changed();self.extension_services.emit('zenit.contributions.changed');return result
        if path=='/extensions/discard':
            if body.get('plan'):self.extensions.discard_plan(body['plan'])
            else:self.extensions.discard(body.get('ticket',''))
            return {'discarded':True}
        if path=='/extensions/toggle':
            self.extension_runtime.invalidate([body.get('id')],'Una extensión se activó o desactivó. Revisa e inicia de nuevo los motores afectados.')
            result=self.extensions.update_state(body.get('id'),body.get('enabled'));self.extension_services.theme_changed();self.extension_services.icons_changed();self.extension_services.emit('zenit.contributions.changed');return result
        if path=='/extensions/remove':
            if body.get('consent') is not True:raise PermissionError('Confirma la desinstalación.')
            self.extension_runtime.invalidate([body.get('id')],'Se desinstaló una dependencia. Revisa los paquetes del motor.')
            result=self.extensions.update_state(body.get('id'),remove=True);self.extension_services.theme_changed();self.extension_services.icons_changed();self.extension_services.emit('zenit.contributions.changed');return result
        if path=='/extensions/updates':return self.extensions.updates()
        if path=='/extensions/export':return self.extensions.export_package(body.get('id'))
        if path=='/terminals/create':return self.terminals.create(ws,body.get('profile'),body.get('consent'),body.get('cols',100),body.get('rows',26),environment=self.extension_services.environment(ws.root))
        if path=='/terminals/write':
            terminal=self._terminal(body.get('id'));written=terminal.write(body.get('data',''))
            return {'ok':written,'closed':terminal.closed}
        if path=='/terminals/claim':return self._terminal(body.get('id')).claim(body.get('view'))
        if path=='/terminals/resize':return {'ok':self._terminal(body.get('id')).resize(body.get('cols',100),body.get('rows',26),body.get('view',''))}
        if path=='/terminals/close':self.terminals.get(body.get('id')).close();return {'closed':True}
        if path=='/development':return self.tools.save(body)
        if path=='/tasks/run':return self.tools.run(ws,body.get('id'),body.get('file',''),body.get('consent'))
        if path=='/tools/plan':return self.tools.plan(body.get('package'),body.get('manager'))
        if path=='/lsp/start':return self.lsp.start(ws,body.get('profile'),body.get('consent'))
        if path=='/lsp/request':self._trusted();return self.lsp.request(body.get('id'),body.get('method'),body.get('params',{}))
        if path=='/lsp/notify':self._trusted();return self.lsp.notify(body.get('id'),body.get('method'),body.get('params',{}))
        if path=='/lsp/stop':return self.lsp.stop(body.get('id'))
        if path=='/ai/credential':return self.ai.vault.set(body.get('provider'),body.get('key'),body.get('remember') is True)
        if path=='/ai/account/login':
            if not self.prefs.get('security.terminals'):raise PermissionError('Activa las terminales para iniciar el cliente oficial.')
            result=self.ai.accounts.login(body.get('provider'),self.terminals)
            if result.get('mode')=='browser':
                import webbrowser
                threading.Thread(target=webbrowser.open,args=(result['url'],),daemon=True).start()
            return result
        if path=='/ai/account/logout':
            if body.get('provider')!='codex':raise ValueError('Cierra la sesión desde el cliente oficial de este proveedor.')
            return self.ai.accounts.codex.logout()
        if path=='/ai/forget':return self.ai.vault.delete(body.get('provider'))
        if path=='/ai/models':return self.ai.models(body.get('provider'),body.get('consent'))
        if path=='/ai/start':
            request=dict(body)
            request['memoryWorkspace']=str(ws.root)
            if request.get('filePlan') is True:
                self._trusted()
                request.update(self.melody_files.prepare(ws,request))
            return self.ai.start(request)
        if path=='/ai/memory/forget':
            key=self.ai.memory.key(str(ws.root),body.get('path',''),body.get('provider',''))
            self.ai.memory.forget(key);self.ai.clear_history();return {'forgotten':True}
        if path=='/ai/files/review':self._trusted();return self.melody_files.review(ws,body.get('job'))
        if path=='/ai/files/apply':self._trusted();return self.melody_files.commit(ws,body.get('ticket'),body.get('consent'))
        if path=='/ai/files/undo':self._trusted();return self.melody_files.undo(ws,body.get('receipt'))
        if path=='/ai/files/test':return self.melody_files.verify(ws,body)
        if path=='/ai/cancel':self.ai.get(body.get('id')).cancel();return {'cancelled':True}
        if path=='/ai/clear':
            self.ai.clear_history()
            return {'cleared':True}
        if path=='/ui/command':
            allowed={'lumen.focus.toggle','lumen.focus.on','lumen.focus.off','lumen.settings.open','lumen.extensions.open','lumen.lantern.open'}
            command=body.get('command')
            if command not in allowed:raise ValueError('Comando de interfaz no admitido.')
            with self.command_lock:
                self.command_seq+=1;self.command_events.append({'seq':self.command_seq,'command':command});self.command_events=self.command_events[-100:]
            return {'queued':True,'sequence':self.command_seq,'command':command}
        raise FileNotFoundError('Operación de plataforma desconocida.')
    def workspace_changed(self):
        self.hilo.cancel_workspace(self.app.workspace.root)
        self.hilo.lifecycle('workspace_stop',self.app.workspace)
        self.hilo.invalidate()
    def shutdown(self):
        self.hilo.shutdown()
