"""Per-provider cancellation, including a bounded cancel-before-request race."""
import re,threading,time
from contextlib import contextmanager

class ProviderOperation:
    def __init__(self,host):self.host=host;self.event=threading.Event();self.wire=None;self.lock=threading.RLock()
    def cancel(self):
        with self.lock:
            self.event.set()
            if self.wire:self.host.send({'type':'cancelRequest','id':self.wire})
    def send(self,message):
        # Publish and send under the same lock as cancellation. Otherwise a
        # queued request can start between its send and a late wire-id bind.
        with self.lock:
            if self.event.is_set():return False
            self.wire=message['id'];self.host.send(message);return True

def key(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',value):raise ValueError('Identificador de consulta inválido.')
    return value

class ProviderOperations:
    def __init__(self,host):self.host=host;self.lock=threading.RLock();self.active={};self.early={}
    def prune(self):
        cutoff=time.monotonic()-60
        self.early={k:v for k,v in self.early.items() if v>cutoff}
        while len(self.early)>256:self.early.pop(next(iter(self.early)))
    def cancel(self,value):
        value=key(value)
        with self.lock:
            self.prune();operation=self.active.get(value)
            if operation:operation.cancel()
            else:self.early[value]=time.monotonic();self.prune()
    @contextmanager
    def begin(self,value=None):
        operation=ProviderOperation(self.host)
        with self.lock:
            self.prune()
            if value is not None:
                value=key(value)
                if value in self.active:raise ValueError('Consulta de extensión duplicada.')
                if len(self.active)>=128:raise ValueError('Demasiadas consultas de extensión pendientes.')
                if value in self.early:self.early.pop(value);operation.event.set()
                self.active[value]=operation
        try:yield operation
        finally:
            with self.lock:
                if value is not None:self.active.pop(value,None)
