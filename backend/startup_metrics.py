"""Bounded wall-clock spans; reading a report never starts optional services."""
from contextlib import contextmanager
import threading
import time


class StartupMetrics:
    def __init__(self,started=None):
        self.started=time.perf_counter() if started is None else started
        self.lock=threading.RLock();self.rows=[]

    @contextmanager
    def phase(self,name,kind='startup'):
        start=time.perf_counter();status='completed'
        try:yield
        except BaseException:
            status='failed';raise
        finally:
            end=time.perf_counter()
            with self.lock:
                self.rows.append({'name':name,'kind':kind,'startMs':round((start-self.started)*1000,3),
                                  'durationMs':round((end-start)*1000,3),'endMs':round((end-self.started)*1000,3),'status':status})
                self.rows=self.rows[-128:]

    def snapshot(self):
        with self.lock:return {'clock':'perf_counter','scope':'Desde la entrada del proceso cuando está disponible; no incluye el lanzador ni Windows. Los intervalos anidados no se suman.',
                               'phases':[dict(row) for row in self.rows]}

    def mark(self,name):
        with self.phase(name,'milestone'):pass
