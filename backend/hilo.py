"""Bounded background work and explicit application handoffs, in the user process."""
from collections import OrderedDict
from concurrent.futures import CancelledError
import copy
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid

from .runtime_paths import find_tool
from .orchestration import Kernel


class Hilo(Kernel):
    def __init__(self, features):
        super().__init__()
        self.features = features
        self.lock = threading.RLock()
        self.queue = queue.PriorityQueue(maxsize=24)
        self.jobs = OrderedDict()
        self.cache = {}
        self.reads = {}
        self.cache_generation=0
        self.sequence = 0
        self.closed = False
        # One maintenance worker leaves foreground execution and HTTP independent.
        self.worker = threading.Thread(target=self._work, name='zenit-hilo', daemon=True)
        self.worker.start()

    def submit(self, label, operation, *, workspace='', key=None, priority=10, cancel=None):
        with self.lock:
            if self.closed: raise RuntimeError('El núcleo se está cerrando.')
            if key:
                existing = next((j for j in self.jobs.values() if j['key'] == key and j['workspace']==str(workspace) and j['state'] in ('queued', 'running')), None)
                if existing: return {'job': existing['id']}
            identity = uuid.uuid4().hex
            event = threading.Event()
            job = dict(id=identity, label=label, workspace=str(workspace), key=key, state='queued', stage='Waiting', priority=priority, created=time.time(), started=None, result=None, error=None, event=event, cancel=cancel)
            self.sequence += 1
            self.jobs[identity] = job
            try: self.queue.put_nowait((priority, self.sequence, identity, operation))
            except queue.Full:
                del self.jobs[identity]
                raise ValueError('Hay 24 operaciones pendientes. Espera o cancela una tarea.') from None
            for old in list(self.jobs):
                if len(self.jobs) <= 64: break
                if self.jobs[old]['state'] not in ('queued', 'running'): del self.jobs[old]
            return {'job': identity}

    def _work(self):
        while True:
            try: _, _, identity, operation = self.queue.get(timeout=.2)
            except queue.Empty:
                if self.closed: return
                continue
            with self.lock: job = self.jobs[identity]
            result = None; error = None
            try:
                if job['event'].is_set(): raise CancelledError()
                with self.lock: job.update(state='running', stage='Preparing', started=time.time())
                result = operation(job['event'])
                state = 'cancelled' if job['event'].is_set() else 'done'
            except CancelledError: state = 'cancelled'
            except Exception as failure:
                state = 'failed'; error = str(failure)[:2000]
            finally:
                with self.lock: job.update(state=state, result=result, error=error, finished=time.time())
                self.queue.task_done()

    def cancel(self, identity):
        with self.lock:
            job = self.jobs.get(identity)
            if not job: raise ValueError('Operación desconocida.')
            if job['state'] in ('queued', 'running'):
                job['event'].set()
                if job['cancel']: job['cancel']()
            return {'cancelled': job['event'].is_set()}

    def report(self, event, stage):
        with self.lock:
            for job in self.jobs.values():
                if job['event'] is event and job['state'] == 'running':
                    job['stage'] = str(stage)[:160]
                    break

    def cancel_workspace(self, workspace):
        for identity, job in list(self.jobs.items()):
            if job['workspace'] == str(workspace): self.cancel(identity)

    def schedule_process(self, job):
        job.queued = True
        def run(event):
            job.queued = False
            if event.is_set(): job.cancel()
            job.run()
            if job.code and not job.cancelled: raise ValueError('Package process failed. ' + job.output[-1800:])
            return {'task': job.id, 'code': job.code}
        def cancel():
            job.cancel()
            if job.queued: job.done = True
        return self.submit('Packages · ' + Path(job.cwd).name, run, workspace=job.cwd, key='process:' + job.id, cancel=cancel)

    def cached(self, key, read, ttl=15):
        # Concurrent windows share one discovery instead of starting identical
        # filesystem/tool scans. Errors wake every waiter and are never cached.
        with self.lock:
            item = self.cache.get(key)
            if item and item[0] > time.monotonic(): return copy.deepcopy(item[1])
            pending=self.reads.get(key)
            owner=pending is None
            if owner:pending={'event':threading.Event(),'generation':self.cache_generation};self.reads[key]=pending
        if not owner:
            if not pending['event'].wait(30):raise TimeoutError('La detección de herramientas sigue ocupada.')
            if 'error' in pending:raise pending['error']
            if pending['generation']!=self.cache_generation:return self.cached(key,read,ttl)
            return copy.deepcopy(pending['value'])
        try:
            value=read()
            with self.lock:
                pending['value']=value
                if pending['generation']==self.cache_generation:self.cache[key]=(time.monotonic()+ttl,value)
                if len(self.cache)>32:self.cache.pop(next(iter(self.cache)))
            return copy.deepcopy(value)
        except BaseException as error:
            pending['error']=error;raise
        finally:
            with self.lock:self.reads.pop(key,None);pending['event'].set()

    def invalidate(self):
        with self.lock:self.cache.clear();self.cache_generation+=1

    def clear_finished(self, workspace):
        with self.lock:
            finished=[identity for identity,job in self.jobs.items() if job['workspace']==str(workspace) and job['state'] not in ('queued','running')]
            for identity in finished:del self.jobs[identity]
        return {'removed':len(finished)}

    def snapshot(self, workspace=None):
        with self.lock:
            jobs = [{k: v for k, v in j.items() if k not in ('event', 'cancel', 'key')} for j in self.jobs.values() if workspace is None or j['workspace'] == str(workspace)]
        pending = sorted((j for j in jobs if j['state'] == 'queued'), key=lambda j:(j['priority'],j['created']))
        for job in jobs:
            job['queuePosition'] = next((i+1 for i,j in enumerate(pending) if j['id']==job['id']), None)
            job['elapsedMs'] = max(0, round(((job.get('finished') or time.time())-(job['started'] or job['created']))*1000))
        counts={state:sum(j['state']==state for j in jobs) for state in ('queued','running','done','failed','cancelled')}
        return {'automatic': True, 'administrator': False, 'workers': 1, 'queueLimit': 24, 'jobs': jobs, 'counts':counts, 'cacheEntries': len(self.cache),'execution':self.features.app.runner.snapshot() if getattr(self.features,'app',None) else None}

    def shutdown(self):
        with self.lifecycle_lock:
            if self.stopping:return
            self.stopping=True
        self.closed = True
        for identity in list(self.jobs): self.cancel(identity)
        self.worker.join(timeout=5)
        self.lifecycle('shutdown')
        self.invalidate()


class Connections:
    """No credentials, arbitrary command strings or implicit external messages."""
    NAMES = {'codex': 'Codex / ChatGPT', 'claude-code': 'Claude Code', 'gemini-cli': 'Gemini', 'blender': 'Blender', 'unity': 'Unity', 'unreal': 'Unreal Engine', 'github': 'GitHub'}
    PURPOSE = {'codex': 'Code and review in the official CLI', 'claude-code': 'Refactor with the official CLI', 'gemini-cli': 'Explore with the official CLI', 'blender': 'Open a scene or run a Python script', 'unity': 'Open the current Unity project', 'unreal': 'Open a .uproject in Unreal Editor', 'github': 'Inspect the repository on GitHub'}

    def __init__(self, features): self.features = features

    def executable(self, name):
        if name in ('codex', 'claude-code', 'gemini-cli'):
            from .accounts import client_argv
            try: return client_argv(name)
            except ValueError: return None
        tool = {'unity': 'Unity', 'unreal': 'UnrealEditor', 'github': 'gh'}.get(name, name)
        if path := find_tool(tool, self.features.runtimes.config.get('tools')): return [path]
        if os.name == 'nt':
            base = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))
            patterns = {'blender': 'Blender Foundation/Blender*/blender.exe', 'unity': 'Unity/Hub/Editor/*/Editor/Unity.exe', 'unreal': 'Epic Games/UE_*/Engine/Binaries/Win64/UnrealEditor.exe', 'github': 'GitHub CLI/gh.exe'}
            found = sorted(base.glob(patterns[name]))
            if found: return [str(found[-1])]
        return None

    def inventory(self):
        return self.features.hilo.cached('connections', lambda: [{'id': name, 'name': label, 'purpose': self.PURPOSE[name], 'available': bool(argv := self.executable(name)), 'executable': argv[0] if argv else None} for name, label in self.NAMES.items()])

    def launch(self, ws, body):
        if not ws.trusted: raise PermissionError('Trust this workspace before opening an application.')
        name = body.get('id')
        if name not in self.NAMES: raise ValueError('Unknown application.')
        argv = self.executable(name)
        if not argv: raise ValueError('Install the official application or configure its executable in Languages and tools.')
        if name in ('codex', 'claude-code', 'gemini-cli'):
            # Reuse the same provider-owned profile as Melody's sign-in panel.
            from .accounts import interactive_argv
            argv = interactive_argv(name, argv)
            environment, home = self.features.ai.accounts.environment(name)
            if name == "codex": environment["CODEX_HOME"] = str(self.features.ai.accounts.codex.home)
            return {'terminal': self.features.hacker._terminal(argv, self.NAMES[name], ws.root, environment)}
        if name == 'github':
            return self.features.app.runner.start([argv + ['repo', 'view', '--json', 'nameWithOwner,url,description']], ws.root, timeout=30)
        if name == 'unity':
            if not ws.resolve('ProjectSettings', must_exist=False).is_dir(): raise ValueError('Open the root of a Unity project first.')
            argv += ['-projectPath', str(ws.root)]
        else:
            path = ws.resolve(body.get('path', ''))
            if not path.is_file(): raise ValueError('Choose a saved scene, script or project file.')
            if name == 'blender' and path.suffix.lower() == '.py':
                return self.features.app.runner.start([argv + ['--background', '--factory-startup', '--python-exit-code', '1', '--python', str(path)]], ws.root, timeout=300)
            suffix = '.blend' if name == 'blender' else '.uproject'
            if path.suffix.lower() != suffix: raise ValueError('This action requires a ' + suffix + ' file.')
            argv += [str(path)]
        # This action explicitly opens the requested external application UI.
        child = subprocess.Popen(argv, cwd=ws.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {'opened': True, 'application': self.NAMES[name], 'pid': child.pid}
