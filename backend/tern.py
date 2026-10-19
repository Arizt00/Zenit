"""Session environments, with explicit .tern checkpoints owned by the workspace."""
from concurrent.futures import CancelledError
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
import uuid
from .preferences import atomic_json


class Tern:
    def __init__(self, features):
        self.features = features
        self.sessions = {}
        self.lock = threading.RLock()
        self.errors = []
        from .tern_portability import TernPortability
        self.portability=TernPortability(self)

    def directory(self, ws, identity):
        if not isinstance(identity, str) or not re.fullmatch('[a-f0-9]{32}', identity): raise ValueError('Invalid environment identity.')
        path = ws.resolve('.lumen/tern/' + identity, must_exist=False)
        # Reject NTFS junctions too, including parents not yet present on creation.
        for candidate in (path, *path.parents):
            if candidate == ws.root: break
            if candidate.exists() and getattr(candidate.lstat(), 'st_file_attributes', 0) & 0x400:
                raise PermissionError('Environment folders cannot use reparse points.')
        return path

    def owned(self, ws, identity):
        directory = self.directory(ws, identity)
        marker = directory / 'owner.json'
        if not marker.is_file() or marker.is_symlink(): raise ValueError('This environment has no Zénit ownership record.')
        record = json.loads(marker.read_text(encoding='utf-8'))
        if record.get('id') != identity or record.get('schema') != 1: raise ValueError('Environment ownership does not match.')
        return directory, record

    def snapshot(self, ws):
        with self.lock:
            for session in self.sessions.values():
                terminal = self.features.terminals.sessions.get(session.get('terminal'))
                if session['state'] == 'running' and (not terminal or terminal.closed): session['state'] = 'ready'
            sessions = [{k: v for k, v in s.items() if k not in ('workspace', 'ws', 'profile')} for s in self.sessions.values() if s['workspace'] == str(ws.root)]
        state = self.features.machines.snapshot()
        return {'sessions': sessions, 'saved': [p.name for p in ws.root.glob('*.tern') if p.is_file() and not p.is_symlink() and not self.features.machine_images.is_descriptor(p)][:100],
                'python': bool(self.features.python_packages.base()), 'vm': state['templates'][0]['available'],
                'bundles':[p.name for p in ws.root.glob('*.tern.zip') if p.is_file() and not p.is_symlink()][:100],'errors': self.errors[-5:]}

    def create(self, ws, body, event):
        if not ws.trusted: raise PermissionError('Trust this workspace before creating an environment.')
        kind = body.get('kind', 'python')
        if kind not in ('python', 'arch'): raise ValueError('Choose Python or Arch Linux.')
        resources = self.resources(body) if kind == 'arch' else {}
        inherit = body.get('inherit', True)
        if not isinstance(inherit, bool): raise ValueError('Choose whether to include the bundled Python packages.')
        name = body.get('name') or ('Python session' if kind == 'python' else 'Arch session')
        if not isinstance(name, str) or not name.strip() or len(name) > 80: raise ValueError('Use an environment name of 1–80 characters.')
        with self.lock:
            if len(self.sessions) >= 8: raise ValueError('Keep at most eight session environments.')
        identity = uuid.uuid4().hex; directory = self.directory(ws, identity)
        directory.mkdir(parents=True)
        atomic_json(directory / 'owner.json', {'schema': 1, 'id': identity, 'kind': kind})
        try:
            session = dict(id=identity, name=name.strip(), kind=kind, saved=None, state='ready', terminal=None, created=time.time(), workspace=str(ws.root), ws=ws)
            if kind == 'python':
                self.features.hilo.report(event, 'Creating Python environment')
                executable = self.features.python_packages.base()
                if not executable: raise ValueError('Python is not installed.')
                session['inherit'] = inherit
                task = self.features.app.runner.start([[executable, '-I', '-m', 'venv', *(['--system-site-packages'] if inherit else []), str(directory / 'environment')]], ws.root, timeout=180)
                job = self.features.app.runner.jobs[task['job']]
                while not job.done:
                    if event.wait(.1): job.cancel()
                if event.is_set(): raise CancelledError()
                if job.code != 0: raise ValueError('Python environment creation failed. ' + job.output[-2000:])
            else:
                self.features.hilo.report(event, 'Preparing virtual machine disk')
                session['profile'] = self.features.machines.create_arch(directory=directory, identity=identity, name=name, persistent=False)
                session['profile'].update(resources)
                session['resources'] = resources
            if event.is_set() or not ws.trusted: raise CancelledError()
            with self.lock: self.sessions[identity] = session
            return {'environment': identity}
        except BaseException:
            self.remove_owned(ws, identity)
            raise

    @staticmethod
    def resources(body):
        if not isinstance(body, dict): raise ValueError('Invalid virtual machine resources.')
        memory, cpus = body.get('memory', 2048), body.get('cpus', 1)
        if type(memory) is not int or memory not in (1024, 2048, 4096, 8192): raise ValueError('Choose 1, 2, 4 or 8 GB of VM memory.')
        if type(cpus) is not int or cpus not in (1, 2, 4): raise ValueError('Choose 1, 2 or 4 virtual CPUs.')
        return {'memory': memory, 'cpus': cpus}

    def get(self, ws, identity):
        session = self.sessions.get(identity)
        if not session or session['workspace'] != str(ws.root): raise ValueError('This environment is not open in this workspace.')
        self.owned(ws, identity)
        return session

    def activate(self, ws, identity):
        if not ws.trusted: raise PermissionError('Trust this workspace before activating an environment.')
        session = self.get(ws, identity)
        if session['kind'] != 'python': raise ValueError('Virtual machines run through their own console.')
        directory, _ = self.owned(ws, identity)
        ws.environment_path = str((directory / 'environment').relative_to(ws.root))
        self.refresh_interpreter(ws)
        for current in self.sessions.values():
            if current['workspace'] == str(ws.root): current['active'] = current is session
        return {'active': identity, 'python': str(self.python(directory))}

    def refresh_interpreter(self, ws):
        manager = self.features.lsp
        profiles = []
        for identity, session in list(manager.sessions.items()):
            if 'python' in session.profile.get('languages', []):
                profiles.append(session.profile['id']); manager.stop(identity)
        self.features.hilo.invalidate()
        self.features.extension_services.emit('zenit.dependencies.changed', workspace=str(ws.root), languages=['python'], profiles=profiles)

    @staticmethod
    def python(directory): return directory / 'environment' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

    def console(self, ws, identity):
        if not ws.trusted: raise PermissionError('Trust this workspace before opening its environment.')
        session = self.get(ws, identity)
        old = self.features.terminals.sessions.get(session.get('terminal'))
        if old and not old.closed: return {'terminal': {'id': old.id, 'profile': old.profile, 'kind': old.kind}}
        directory, _ = self.owned(ws, identity)
        if session['kind'] == 'arch':
            terminal = self.features.machines.start(ws, identity, profile=session['profile'])
        else:
            self.activate(ws, identity)
            terminal = self.features.hacker._terminal([str(self.python(directory)), '-i'], session['name'], ws.root, {'VIRTUAL_ENV': str(directory / 'environment')})
        session['terminal'] = terminal['id']; session['state'] = 'running'
        return {'terminal': terminal}

    def save(self, ws, identity, filename):
        session = self.get(ws, identity)
        if not ws.trusted: raise PermissionError('Trust this workspace before saving an environment.')
        if not isinstance(filename, str) or not re.fullmatch(r'[\w -]{1,80}\.tern', filename): raise ValueError('Use a filename such as experiment.tern in the workspace root.')
        descriptor = self.portability.describe(ws,session)
        # Only a descriptor already owned by this open session can be refreshed.
        previous=ws.read(filename)['revision'] if session['saved']==filename else None
        ws.save(filename, json.dumps(descriptor, ensure_ascii=False, indent=2) + '\n', previous, create=session['saved']!=filename)
        session['saved'] = filename
        return {'file': filename}

    def reopen(self, ws, filename):
        if not ws.trusted: raise PermissionError('Trust this workspace before restoring an environment.')
        path = ws.resolve(filename)
        if path.suffix != '.tern' or path.stat().st_size > 1000000: raise ValueError('Invalid .tern descriptor.')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema') not in (1,2) or data.get('type') != 'zenit-environment': raise ValueError('Unsupported .tern format.')
        if data['schema']==2:self.portability.validate(data)
        identity = data.get('id'); directory, record = self.owned(ws, identity)
        if data.get('kind') not in ('python', 'arch') or data['kind'] != record.get('kind'): raise ValueError('Environment type does not match its files.')
        with self.lock:
            if identity in self.sessions:
                self.get(ws, identity)
                return {'environment': identity}
            if len(self.sessions) >= 8: raise ValueError('Keep at most eight session environments.')
        session = dict(id=identity, name=str(data.get('name', 'Environment'))[:80], kind=data['kind'], saved=path.name, state='ready', terminal=None, created=data.get('created'), workspace=str(ws.root), ws=ws)
        if session['kind'] == 'arch':
            session['resources'] = self.resources(data.get('resources', {}))
            if not all((directory / file).is_file() and not (directory / file).is_symlink() for file in ('disk.qcow2', 'seed.iso')): raise ValueError('The saved VM disk or seed is missing.')
            session['profile'] = {'id': identity, 'name': session['name'], 'type': 'arch', 'disk': str(directory / 'disk.qcow2'), 'seed': str(directory / 'seed.iso'), **session['resources']}
        elif not self.python(directory).is_file(): raise ValueError('The Python environment files are missing.')
        else: session['inherit'] = data.get('sourceInherit',data.get('inherit', True)) is True
        with self.lock: self.sessions[identity] = session
        return {'environment': identity}

    def remove_owned(self, ws, identity):
        directory, _ = self.owned(ws, identity)
        expected = ws.root / '.lumen' / 'tern' / identity
        if directory != expected.resolve() or not directory.is_relative_to(ws.root): raise PermissionError('Environment cleanup left its workspace.')
        # shutil does not traverse directory junctions; the checked root is never a link.
        shutil.rmtree(directory)

    def stop(self, ws, identity):
        session = self.get(ws, identity)
        directory, _ = self.owned(ws, identity)
        if session['kind'] == 'arch': self.features.machines.stop(identity)
        else:
            terminal = self.features.terminals.sessions.get(session.get('terminal'))
            if terminal and not terminal.closed: terminal.close()
        if session.get('active'):
            self.features.lantern.stop(); self.features.debugger.stop()
            ws.environment_path = '.venv'; self.refresh_interpreter(ws)
        def uses_environment(argv):
            return any(isinstance(arg, str) and Path(arg).is_absolute() and Path(arg).resolve().is_relative_to(directory) for arg in argv)
        for terminal in list(self.features.terminals.sessions.values()):
            if not terminal.closed and uses_environment(terminal.profile.get('argv', [])): terminal.close()
        for job in list(self.features.app.runner.jobs.values()):
            if not job.done and any(isinstance(command, list) and uses_environment(command) for command in job.commands):
                job.cancel()
                deadline = time.monotonic() + 5
                while not job.done and time.monotonic() < deadline: time.sleep(.03)
                if not job.done: raise ValueError('An environment task is still closing. Retry in a moment.')
        if not session['saved']: self.remove_owned(ws, identity)
        del self.sessions[identity]
        return {'closed': identity, 'retained': bool(session['saved'])}

    def close_workspace(self, ws):
        for identity, session in list(self.sessions.items()):
            if session['workspace'] != str(ws.root): continue
            try: self.stop(ws, identity)
            except Exception as error: self.errors.append(str(error))
