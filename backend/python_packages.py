"""Project-scoped Python packages. The shipped interpreter is never modified."""
import importlib.metadata
import os
from pathlib import Path
import sys
import threading
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name
from .foundation import bundled_tool, inventory, tool_environment
from .runtime_paths import find_tool


def environment_python(workspace):
    folder=workspace.resolve('.venv',must_exist=False)
    python=folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    return folder,python


def installed_packages(folder):
    if not folder.is_dir():return []
    items={}
    for dist in importlib.metadata.distributions(path=[str(folder)]):
        name=dist.metadata.get('Name')
        if name:items[name.lower()]={'name':name,'version':dist.version,'summary':dist.metadata.get('Summary','')[:400]}
    return sorted(items.values(),key=lambda x:x['name'].lower())


class PythonPackages:
    def __init__(self,features):self.features=features;self.jobs={};self.lock=threading.RLock()
    def base(self):
        python=find_tool('python',self.features.runtimes.config.get('tools'))
        if not python and not getattr(sys,'frozen',False):python=sys.executable
        return python
    def status(self,ws):
        base=self.base();folder,python=environment_python(ws)
        site=ws.resolve('.venv/'+('Lib/site-packages' if os.name=='nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'),must_exist=False)
        # POSIX project Python may have a different minor version from the host.
        sites=[site] if os.name=='nt' else [p for p in folder.glob('lib/python*/site-packages') if p.resolve().is_relative_to(folder)]
        packages=[item for path in sites for item in installed_packages(path)]
        root,data=inventory();component=next((c for c in data.get('components',[]) if c.get('id')=='python'),{})
        base_site=Path(base).parent/'Lib/site-packages' if base and os.name=='nt' else None
        base_packages=installed_packages(base_site) if base_site else []
        with self.lock:
            job=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
            task={'id':job.id,'done':job.done,'code':job.code,'output':job.output[-24000:]} if job else None
        bundled=bool(base and base==bundled_tool('python'))
        return {'base':{'path':base,'bundled':bundled,'version':component.get('version','') if bundled else '','packages':base_packages},
                'environment':{'directory':str(folder),'python':str(python),'ready':python.is_file() and (folder/'pyvenv.cfg').is_file()},
                'packages':packages,'requirements':ws.resolve('requirements.txt',must_exist=False).is_file(),'task':task}
    def start(self,ws,body):
        if not ws.trusted:raise PermissionError('Trust this project before managing Python packages.')
        operation=body.get('action')
        if operation not in ('create','install','upgrade','uninstall','requirements','check'):raise ValueError('Unknown Python package action.')
        requirement=None
        if operation in ('install','upgrade','uninstall'):
            text=body.get('requirement')
            if not isinstance(text,str) or not text.strip() or len(text)>1000 or any(c in text for c in '\r\n\0'):raise ValueError('Enter one package requirement, for example requests>=2.32.')
            try:requirement=Requirement(text)
            except InvalidRequirement as exc:raise ValueError('Invalid package requirement.') from exc
            if requirement.url:raise ValueError('Use a package name from the package index here. Direct URLs are not supported.')
            if operation!='install' and (requirement.extras or requirement.specifier or requirement.marker):raise ValueError('Use only the package name for update or removal.')
        base=self.base()
        if not base:raise ValueError('The standalone Python runtime is unavailable.')
        folder,python=environment_python(ws);ready=python.is_file() and (folder/'pyvenv.cfg').is_file()
        if folder.exists() and not ready:raise ValueError('The existing .venv is incomplete. It has been preserved; repair it or choose a different project.')
        if operation=='uninstall' and not ready:raise ValueError('There is no project environment to remove a package from.')
        commands=[]
        if not ready:commands.append([base,'-I','-m','venv','--system-site-packages',str(folder)])
        pip=[str(python),'-I','-m','pip','--isolated','--disable-pip-version-check']
        if operation=='install':commands.append([*pip,'install','--no-input',str(requirement)])
        elif operation=='upgrade':commands.append([*pip,'install','--no-input','--upgrade',requirement.name])
        elif operation=='uninstall':
            if canonicalize_name(requirement.name)=='pip':raise ValueError('pip is required to manage this project environment and cannot be removed here.')
            local={canonicalize_name(x['name']) for x in self.status(ws)['packages']}
            if canonicalize_name(requirement.name) not in local:raise ValueError('Only project-local packages can be removed. Bundled packages are read-only.')
            commands.append([*pip,'uninstall','--yes',requirement.name])
        elif operation=='requirements':commands.append([*pip,'install','--no-input','-r',str(ws.resolve('requirements.txt'))])
        elif operation=='check':commands.append([*pip,'check'])
        if not commands:return {'environmentReady':True}
        with self.lock:
            previous=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
            if previous and not previous.done:raise ValueError('A Python package operation is already running for this project.')
            task=self.features.app.runner.start(commands,ws.root,timeout=900,env={**tool_environment(),'PIP_REQUIRE_VIRTUALENV':'true','PYTHONUTF8':'1'})
            self.jobs[str(ws.root)]=task['job'];return task
    def cancel(self,ws):
        if not ws.trusted:raise PermissionError('Trust this project before cancelling its Python task.')
        with self.lock:
            job=self.features.app.runner.jobs.get(self.jobs.get(str(ws.root)))
            if job and not job.done:job.cancel()
        return {'cancelled':True}
