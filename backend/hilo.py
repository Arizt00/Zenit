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
        from .resource_budget import ResourceBudget
        self.budget=ResourceBudget(features.prefs if features else None)
        if features:features.app.runner.governor=self.budget
        self.lock = threading.RLock()
        self.queue = queue.PriorityQueue(maxsize=24)
        self.interactive_queue=queue.PriorityQueue(maxsize=24);self.interactive_worker=None
        self.jobs = OrderedDict()
        self.cache = {}
        self.reads = {}
        self.cache_generation=0
        self.cache_metrics={'hits':0,'misses':0,'shared':0,'discarded':0,'failures':0,'readMs':0}
        self.sequence = 0
        self.closed = False
        # One maintenance worker leaves foreground execution and HTTP independent.
        self.worker = threading.Thread(target=self._work, name='zenit-hilo', daemon=True)
        self.worker.start()

    def submit(self, label, operation, *, workspace='', key=None, priority=10, cancel=None, depends=()):
        with self.lock:
            if self.closed: raise RuntimeError('El núcleo se está cerrando.')
            if type(priority) is not int or not -20<=priority<=20:raise ValueError('La prioridad debe estar entre -20 y 20.')
            if not isinstance(depends,(list,tuple)) or len(depends)>16 or any(not isinstance(x,str) or x not in self.jobs for x in depends):raise ValueError('Dependencias de tareas no válidas.')
            if any(self.jobs[x]['workspace']!=str(workspace) for x in depends):raise ValueError('Las dependencias deben pertenecer al mismo proyecto.')
            if key:
                existing = next((j for j in self.jobs.values() if j['key'] == key and j['workspace']==str(workspace) and j['state'] in ('queued', 'running')), None)
                if existing: return {'job': existing['id']}
            if sum(j['state']=='queued' for j in self.jobs.values())>=24:raise ValueError('Hay 24 operaciones pendientes. Espera o cancela una tarea.')
            identity = uuid.uuid4().hex
            event = threading.Event()
            job = dict(id=identity, label=label, workspace=str(workspace), key=key, state='queued', stage='Waiting', priority=priority, created=time.time(), started=None, result=None, error=None, event=event, cancel=cancel, depends=list(dict.fromkeys(depends)), operation=operation, enqueued=False)
            self.sequence += 1
            self.jobs[identity] = job
            self._release_waiting()
            referenced={x for j in self.jobs.values() if j['state'] in ('queued','running') for x in j['depends']}
            for old in list(self.jobs):
                if len(self.jobs) <= 64: break
                if self.jobs[old]['state'] not in ('queued', 'running') and old not in referenced and not self.jobs[old]['enqueued']: del self.jobs[old]
            return {'job': identity}

    def _release_waiting(self):
        # Only ready work enters the queue. A high-priority dependent cannot
        # occupy the worker while its lower-priority prerequisite is waiting.
        for job in self.jobs.values():
            if job['state']!='queued' or job['enqueued']:continue
            prerequisites=[self.jobs[x] for x in job['depends'] if x in self.jobs]
            if any(x['state'] in ('failed','cancelled') for x in prerequisites):
                job['event'].set();job.update(state='cancelled',stage='Dependencia no completada',finished=time.time())
                self._cancel_cleanup(job)
                continue
            if any(x['state']!='done' for x in prerequisites):job['stage']='Esperando otros trabajos';continue
            self.sequence+=1
            work_queue=self.interactive_queue if job['priority']<0 else self.queue
            try:
                work_queue.put_nowait((job['priority'],self.sequence,job['id'],job['operation']));job['enqueued']=True
                if work_queue is self.interactive_queue and (not self.interactive_worker or not self.interactive_worker.is_alive()):
                    self.interactive_worker=threading.Thread(target=self._work,args=(work_queue,),name='zenit-interaction',daemon=True);self.interactive_worker.start()
            except queue.Full:break

    def _work(self,work_queue=None):
        work_queue=self.queue if work_queue is None else work_queue
        while True:
            try: _, _, identity, operation = work_queue.get(timeout=.2)
            except queue.Empty:
                if self.closed: return
                if work_queue is self.interactive_queue:
                    with self.lock:
                        if work_queue.empty():self.interactive_worker=None;return
                continue
            with self.lock:
                job = self.jobs.get(identity)
                if job:
                    job['enqueued']=False
                    if job['state']!='queued':job=None
                    else:job.update(state='running',stage='Preparing',started=time.time())
            if job is None:work_queue.task_done();continue
            result = None; error = None
            cpu_started=time.thread_time()
            try:
                if job['event'].is_set(): raise CancelledError()
                result = operation(job['event'])
                state = 'cancelled' if job['event'].is_set() else 'done'
            except CancelledError: state = 'cancelled'
            except Exception as failure:
                state = 'failed'; error = str(failure)[:2000]
            finally:
                with self.lock:
                    job.update(state=state, result=result, error=error, finished=time.time(),workerCpuMs=round((time.thread_time()-cpu_started)*1000,2))
                    self._release_waiting()
                work_queue.task_done()

    def cancel(self, identity):
        with self.lock:
            job = self.jobs.get(identity)
            if not job: raise ValueError('Operación desconocida.')
            if job['state'] in ('queued', 'running'):
                job['event'].set()
                self._cancel_cleanup(job)
                if job['state']=='queued':job.update(state='cancelled',stage='Cancelada',finished=time.time())
                self._release_waiting()
            return {'cancelled': job['event'].is_set()}

    @staticmethod
    def _cancel_cleanup(job):
        # A failed adapter cleanup must not terminate the only scheduler worker
        # or prevent dependent jobs from being cancelled.
        if job['cancel']:
            try:job['cancel']()
            except Exception as error:job['cleanupError']=str(error)[:1000]

    def report(self, event, stage):
        with self.lock:
            for job in self.jobs.values():
                if job['event'] is event and job['state'] == 'running':
                    job['stage'] = str(stage)[:160]
                    break

    def prioritize(self,identity,priority):
        import heapq
        if type(priority) is not int or not -20<=priority<=20:raise ValueError('Prioridad inválida.')
        with self.lock:
            job=self.jobs.get(identity)
            if not job or job['state']!='queued':raise ValueError('Solo puede cambiarse la prioridad de una tarea en cola.')
            job['priority']=priority
            for work_queue in (self.queue,self.interactive_queue):
                removed=False
                with work_queue.mutex:
                    kept=[entry for entry in work_queue.queue if entry[2]!=identity]
                    if len(kept)!=len(work_queue.queue):
                        work_queue.queue=kept;heapq.heapify(work_queue.queue);removed=True;work_queue.not_full.notify()
                if removed:work_queue.task_done();job['enqueued']=False;break
            self._release_waiting()
        return {'priority':priority}

    def resources(self,workspace):
        """Read our process tree only, on demand while the task center is visible."""
        ps=getattr(self.features.hardware,'ps',None);execution=[];runner=self.features.app.runner
        def measure(pid):
            if not ps:return None
            try:process=ps.Process(pid);processes=[process,*process.children(recursive=True)]
            except ps.Error:return None
            cpu=0;rss=0;count=0
            for child in processes[:256]:
                try:times=child.cpu_times();cpu+=times.user+times.system;rss+=child.memory_info().rss;count+=1
                except ps.Error:pass
            return {'cpuSeconds':round(cpu,3),'rssBytes':rss,'processes':count}
        with runner.lock:
            for job in runner.jobs.values():
                if str(job.cwd)!=str(workspace):continue
                with job.lock:
                    process=job.process;execution.append({'id':job.id,'label':Path(job.commands[-1][0]).name if job.commands and isinstance(job.commands[-1],list) else 'Ejecución','state':'cancelled' if job.cancelled else 'failed' if job.done and job.code else 'done' if job.done else 'queued' if getattr(job,'queued',False) else 'running','code':job.code,'resources':measure(process.pid) if process and process.poll() is None else None})
        return {'sampledAt':time.time(),'application':measure(os.getpid()),'execution':execution,'budget':self.budget.snapshot(),'scope':'Zénit y sus procesos hijos; RSS sumada, CPU acumulada en segundos','available':ps is not None}

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

    def cached(self, key, read, ttl=15, *, cancel=None):
        # Concurrent windows share one discovery instead of starting identical
        # filesystem/tool scans. Errors wake every waiter and are never cached.
        deadline=time.monotonic()+30
        while True:
            if self.closed or cancel is not None and cancel.is_set():raise CancelledError()
            if time.monotonic()>deadline:raise TimeoutError('La detección de herramientas sigue ocupada.')
            with self.lock:
                item = self.cache.get(key)
                if item and item[0] > time.monotonic():
                    self.cache_metrics['hits']+=1
                    return copy.deepcopy(item[1])
                self.cache.pop(key,None)
                pending=self.reads.get(key)
                owner=pending is None
                if owner:
                    pending={'event':threading.Event(),'generation':self.cache_generation};self.reads[key]=pending
                    self.cache_metrics['misses']+=1
                else:self.cache_metrics['shared']+=1
            if not owner:
                while not pending['event'].wait(.05):
                    if self.closed or cancel is not None and cancel.is_set():raise CancelledError()
                    if time.monotonic()>deadline:raise TimeoutError('La detección de herramientas sigue ocupada.')
                if self.closed or cancel is not None and cancel.is_set():raise CancelledError()
                if pending['generation']!=self.cache_generation:continue
                if 'error' in pending:raise pending['error']
                return copy.deepcopy(pending['value'])
            started=time.monotonic()
            try:
                value=read()
                with self.lock:
                    pending['value']=value
                    current=pending['generation']==self.cache_generation and not self.closed
                    if current:self.cache[key]=(time.monotonic()+ttl,value)
                    else:self.cache_metrics['discarded']+=1
                    if len(self.cache)>32:self.cache.pop(next(iter(self.cache)))
            except BaseException as error:
                with self.lock:pending['error']=error;self.cache_metrics['failures']+=1
                raise
            finally:
                with self.lock:
                    self.cache_metrics['readMs']+=round((time.monotonic()-started)*1000,2)
                    self.reads.pop(key,None);pending['event'].set()
            # A settings/SDK change invalidates the initiating caller too.
            # Previously only waiters retried and the owner saw the old result.
            if current:
                if cancel is not None and cancel.is_set():raise CancelledError()
                return copy.deepcopy(value)

    def cache_stats(self):
        with self.lock:return {**self.cache_metrics,'active':len(self.reads),'entries':len(self.cache)}

    def invalidate(self):
        with self.lock:self.cache.clear();self.cache_generation+=1

    def clear_finished(self, workspace):
        with self.lock:
            referenced={x for j in self.jobs.values() if j['state'] in ('queued','running') for x in j['depends']}
            finished=[identity for identity,job in self.jobs.items() if job['workspace']==str(workspace) and job['state'] not in ('queued','running') and identity not in referenced and not job['enqueued']]
            for identity in finished:del self.jobs[identity]
        return {'removed':len(finished)}

    def snapshot(self, workspace=None):
        with self.lock:
            jobs = [{k: v for k, v in j.items() if k not in ('event', 'cancel', 'key','operation','enqueued')} for j in self.jobs.values() if workspace is None or j['workspace'] == str(workspace)]
            workers=1+int(bool(self.interactive_worker and self.interactive_worker.is_alive()))
        pending = sorted((j for j in jobs if j['state'] == 'queued'), key=lambda j:(j['priority'],j['created']))
        for job in jobs:
            job['queuePosition'] = next((i+1 for i,j in enumerate(pending) if j['id']==job['id']), None)
            job['elapsedMs'] = max(0, round(((job.get('finished') or time.time())-(job['started'] or job['created']))*1000))
        counts={state:sum(j['state']==state for j in jobs) for state in ('queued','running','done','failed','cancelled')}
        return {'automatic': True, 'administrator': False, 'workers': workers, 'queueLimit': 24, 'jobs': jobs, 'counts':counts, 'cacheEntries': len(self.cache),'execution':self.features.app.runner.snapshot() if getattr(self.features,'app',None) else None}

    def shutdown(self):
        with self.lifecycle_lock:
            if self.stopping:return
            self.stopping=True
        self.closed = True
        for identity in list(self.jobs): self.cancel(identity)
        self.worker.join(timeout=5)
        interactive=self.interactive_worker
        if interactive:interactive.join(timeout=5)
        self.lifecycle('shutdown')
        if not self.budget.closed:self.budget.shutdown()
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
