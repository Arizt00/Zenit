"""Optional HILO services are constructed once, only when first requested."""
import importlib
import threading

FACTORIES={
    'investigations':('investigations','Investigations','features'),
    'language_verification':('language_verification','LanguageVerification','features'),
    'hardware':('hardware','HardwareMonitor','prefs'),
    'debugger':('debug_manager','DebugManager','debug'),
    'simulation':('simulation','Simulation','features'),
    'machines':('machines','Machines','features'),
    'machine_images':('machine_images','MachineImages','features'),
    'voice':('melody_voice','MelodyVoice','prefs'),
    'python_packages':('python_packages','PythonPackages','features'),
    'native_packages':('native_packages','NativePackages','features'),
    'tern':('tern','Tern','features'),
    'team':('team','TeamService','features'),
    'binary_tools':('binary_tools','BinaryTools','features'),
    'tests':('project_tests','ProjectTests','features'),
    'conflicts':('git_conflicts','GitConflicts','features'),
    'git_workbench':('git_workbench','GitWorkbench','features'),
    'workflows':('project_workflows','ProjectWorkflows','features'),
    'organizer':('project_organizer','ProjectOrganizer','features'),
    'countercheck':('melody_countercheck','MelodyCountercheck','features'),
    'lantern_matrix':('lantern_matrix','LanternMatrix','features'),
    'lantern_regression':('lantern_regression','LanternRegression','features'),
}


class DeferredServices:
    def setup_deferred(self):self._deferred_lock=threading.RLock()

    def __getattr__(self,name):
        factory=FACTORIES.get(name)
        if factory is None:raise AttributeError(name)
        with self._deferred_lock:
            if name in self.__dict__:return self.__dict__[name]
            if self.__dict__.get('_services_closing') or self.__dict__.get('hilo') and self.hilo.stopping:raise RuntimeError('Zénit se está cerrando; no se iniciarán servicios nuevos.')
            module,kind,argument=factory
            with self.app.timings.phase('service.'+name,'optional'):
                constructor=getattr(importlib.import_module('.'+module,'backend'),kind)
                args=(self.prefs,) if argument=='prefs' else (self.runtimes,self.app.runner) if argument=='debug' else (self,)
                result=constructor(*args)
            self.__dict__[name]=result
            return result

    def optional_call(self,name,method,*args):
        with self._deferred_lock:service=self.__dict__.get(name)
        if service is not None:return getattr(service,method)(*args)

    def deferred_snapshot(self):
        with self._deferred_lock:return [{'id':name,'initialized':name in self.__dict__} for name in FACTORIES]
