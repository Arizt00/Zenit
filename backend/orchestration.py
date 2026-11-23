"""HILO: Hyper Integrated Logic Orchestrator, private modular service lifecycle."""
from collections import OrderedDict, deque
import threading
import time


class Kernel:
    def __init__(self):
        self.services=OrderedDict();self.lifecycle_lock=threading.RLock()
        self.lifecycle_errors=deque(maxlen=32);self.listeners={};self.listener_sequence=0
        self.stopping=False

    def register(self,name,service,*,depends=(),workspace_stop=None,shutdown=None):
        with self.lifecycle_lock:
            if self.stopping:raise RuntimeError('El núcleo se está cerrando.')
            if name in self.services:raise ValueError('Subsystem already registered: '+name)
            if any(key not in self.services for key in depends):raise ValueError('Register dependencies first: '+name)
            self.services[name]={'service':service,'depends':tuple(depends),'workspace_stop':workspace_stop,'shutdown':shutdown}
        return service

    def resolve(self,name):
        with self.lifecycle_lock:
            entry=self.services[name];service=entry['service'];factory=entry.get('factory')
        if service is None and factory:
            with entry['create_lock']:
                with self.lifecycle_lock:
                    if self.stopping:raise RuntimeError('El núcleo se está cerrando.')
                    service=entry['service']
                if service is None:
                    service=factory()
                    with self.lifecycle_lock:entry['service']=service
        return service

    def register_deferred(self,name,factory,**options):
        self.register(name,None,**options)
        with self.lifecycle_lock:self.services[name].update(factory=factory,create_lock=threading.RLock())

    def subscribe(self,event,callback):
        with self.lifecycle_lock:
            self.listener_sequence+=1;key=self.listener_sequence
            self.listeners.setdefault(event,{})[key]=callback
        def remove():
            with self.lifecycle_lock:self.listeners.get(event,{}).pop(key,None)
        return remove

    def emit(self,event,**data):
        with self.lifecycle_lock:callbacks=list(self.listeners.get(event,{}).values())
        for callback in callbacks:
            try:callback(dict(data))
            except Exception as error:self._failure(event,error)

    def _failure(self,name,error):
        with self.lifecycle_lock:self.lifecycle_errors.append({'subsystem':name,'error':str(error)[:500],'time':time.time()})

    def lifecycle(self,phase,*args):
        # Dependants stop before their dependencies. Slow processes run in
        # their own executors; the kernel never funnels execution into one queue.
        with self.lifecycle_lock:items=list(reversed(self.services.items()))
        for name,entry in items:
            callback=entry.get(phase)
            if callback:
                try:callback(*args)
                except Exception as error:self._failure(name,error)
        self.emit(phase,workspace=str(args[0].root) if args else None)

    def kernel_snapshot(self):
        with self.lifecycle_lock:
            return {'name':'Hyper Integrated Logic Orchestrator','subsystems':[{'id':name,'depends':list(entry['depends'])} for name,entry in self.services.items()],'errors':list(self.lifecycle_errors)}
