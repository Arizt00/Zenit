"""Shared tool-process budgets. No polling or CPU restrictions on the IDE itself."""
import math,os,threading,time


class ResourceBudget:
    def __init__(self,prefs):
        self.prefs=prefs;self.lock=threading.RLock();self.entries={};self.thread=None;self.closed=False;self.last={};self.ps=None
    def limits(self):
        cores=(self.prefs.get('hardware.toolCores') if self.prefs else 0) or max(1,(os.cpu_count() or 2)//2)
        memory=self.prefs.get('hardware.toolMemoryMB') if self.prefs else 4096
        return {'cores':cores,'memoryBytes':memory*1024**2,'sampleMs':250,'scope':'Procesos de ejecución registrados, no la interfaz. La RAM es RSS agregada muestreada; el límite de CPU utiliza afinidad cuando el sistema la admite.'}
    def environment(self):
        cores=str(self.limits()['cores'])
        return {'CMAKE_BUILD_PARALLEL_LEVEL':cores,'CARGO_BUILD_JOBS':cores,'OMP_NUM_THREADS':cores,'OPENBLAS_NUM_THREADS':cores}
    def watch(self,identity,pid,done,cancel,background=False,reason=None):
        self.cancel_tree(identity)
        try:
            import psutil
            self.ps=psutil;process=psutil.Process(pid);stamp=process.create_time()
            # Restrict only our explicitly registered tool. Children inherit the
            # same pool; no affinity, priority or settings change on the editor.
            try:
                allowed=psutil.Process(os.getpid()).cpu_affinity();process.cpu_affinity(allowed[:min(len(allowed),self.limits()['cores'])])
                if background:process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name=='nt' else 10)
                affinity=True
            except (AttributeError,psutil.Error,ValueError):affinity=False
        except (ImportError,OSError):return
        except Exception as error:
            if self.ps and isinstance(error,self.ps.Error):return
            raise
        with self.lock:
            if self.closed:return
            self.entries[identity]={'pid':pid,'stamp':stamp,'known':{pid:stamp},'done':done,'cancel':cancel,'background':background,'reason':reason,'affinity':affinity,'cores':self.limits()['cores'],'rss':0}
            if not self.thread or not self.thread.is_alive():
                self.thread=threading.Thread(target=self._monitor,name='zenit-tool-budget',daemon=True);self.thread.start()
    def attach(self,job):
        self.watch(job.id,job.process.pid,lambda:job.done,job.cancel,getattr(job,'resource_class','foreground')=='background',lambda text:(setattr(job,'budget_reason',text),job.append('\n'+text+'\n')))
    def processes(self,entry):
        ps=self.ps;found=[]
        for pid,stamp in list(entry['known'].items()):
            try:
                process=ps.Process(pid)
                if process.create_time()!=stamp:continue
                found.append(process)
                for child in process.children(recursive=True):
                    if len(entry['known'])<256:entry['known'].setdefault(child.pid,child.create_time())
            except ps.Error:pass
        # Include children discovered on this sample without waiting another tick.
        present={p.pid for p in found}
        for pid,stamp in list(entry['known'].items()):
            if pid in present:continue
            try:
                process=ps.Process(pid)
                if process.create_time()==stamp:found.append(process)
            except ps.Error:pass
        return found
    def cancel_tree(self,identity):
        with self.lock:entry=self.entries.get(identity)
        if not entry or not self.ps:return
        for process in reversed(self.processes(entry)):
            try:process.kill()
            except self.ps.Error:pass
    def _monitor(self):
        while True:
            with self.lock:
                if self.closed:return
                entries=list(self.entries.items())
                if not entries:
                    self.last.update(rssBytes=0,registered=0,affinityApplied=True);self.thread=None;return
            total=0;victims=[];limits=self.limits()
            for identity,entry in entries:
                processes=self.processes(entry);rss=0
                if entry['cores']!=limits['cores']:
                    try:
                        allowed=self.ps.Process(os.getpid()).cpu_affinity()[:limits['cores']]
                        for process in processes:process.cpu_affinity(allowed)
                        entry['affinity']=True
                    except (AttributeError,self.ps.Error,ValueError):entry['affinity']=False
                    entry['cores']=limits['cores']
                for process in processes:
                    try:rss+=process.memory_info().rss
                    except self.ps.Error:pass
                entry['rss']=rss;total+=rss
                if entry['done']():
                    # A tool may leave a child holding stdout after its parent
                    # exits. A completed registered run must not orphan it.
                    self.cancel_tree(identity)
                    with self.lock:self.entries.pop(identity,None)
                elif rss:victims.append((not entry['background'],-rss,identity,entry))
            with self.lock:self.last={'rssBytes':total,'registered':len(self.entries),'affinityApplied':all(x['affinity'] for x in self.entries.values()),**limits}
            if total>limits['memoryBytes'] and victims:
                _,_,identity,entry=min(victims);message='La ejecución alcanzó el presupuesto global de memoria de las herramientas.'
                if entry['reason']:entry['reason'](message)
                entry['cancel']();self.cancel_tree(identity)
            time.sleep(.25)
    def snapshot(self):
        with self.lock:return {**self.last,**self.limits(),'active':len(self.entries),'available':self.ps is not None}
    def shutdown(self):
        with self.lock:self.closed=True;entries=list(self.entries.items())
        for identity,entry in entries:entry['cancel']();self.cancel_tree(identity)
        if self.thread and self.thread is not threading.current_thread():self.thread.join(timeout=2)
