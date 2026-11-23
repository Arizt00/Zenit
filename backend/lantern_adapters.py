"""Live adapters stage a buffer and validate it before any user code is executed."""
from __future__ import annotations
import ast
import os
from pathlib import Path
import shutil
import sys
from .workspace import Workspace, MAX_FILE
from .runtimes import language

SKIP = {'.git', '.lumen', '.ncc', 'node_modules', '__pycache__', '.venv', 'venv', 'Library', 'Temp', 'obj', 'bin', 'target', 'dist', 'build'}

class Superseded(Exception): pass

def buffer_sources(workspace, path, content, buffers=None):
    """Validate a bounded set of editor sources before making a private copy."""
    if buffers is None: buffers=[]
    if not isinstance(buffers,list) or len(buffers)>199:
        raise ValueError('Lantern admite hasta 200 archivos abiertos por revisión.')
    active=workspace.resolve(path,must_exist=False).relative_to(workspace.root).as_posix()
    sources={};names=set();total=0
    for row in [*buffers,{'path':active,'content':content}]:
        if not isinstance(row,dict):raise ValueError('Búfer de contexto no válido.')
        name=workspace.resolve(row.get('path'),must_exist=False).relative_to(workspace.root).as_posix()
        if any(part in SKIP or part.startswith('.env') for part in Path(name).parts):
            raise ValueError('Lantern no copia búferes privados o generados: '+name)
        text=row.get('content')
        if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_FILE:
            raise ValueError('Cada búfer de Lantern admite hasta 2 MiB.')
        key=os.path.normcase(name)
        if key in names:raise ValueError('Búfer de contexto repetido: '+name)
        names.add(key);sources[name]=text;total+=len(text.encode('utf-8'))
    if total>4*1024*1024:raise ValueError('Los búferes de Lantern superan 4 MiB. Guarda o cierra algunos archivos antes de continuar.')
    return sources


def stage(workspace, path, content, directory, obsolete, buffers=None):
    """A bounded private project copy, never links to mutable original sources."""
    sources=buffer_sources(workspace,path,content,buffers)
    replacements={os.path.normcase(name) for name in sources}
    directory.mkdir(parents=True, exist_ok=True)
    count = total = 0
    for folder, dirs, files in os.walk(workspace.root, followlinks=False):
        if obsolete(): raise Superseded()
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in dirs + files:
            item = Path(folder) / name
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                raise ValueError('Lantern no copia enlaces del proyecto: ' + str(item.relative_to(workspace.root)))
        for name in files:
            if obsolete(): raise Superseded()
            source = Path(folder) / name
            relative = source.relative_to(workspace.root)
            # Exclude secrets, VCS internals and bytecode from the execution copy.
            if name.startswith('.env') or source.suffix == '.pyc': continue
            if os.path.normcase(relative.as_posix()) in replacements: continue
            count += 1; total += source.stat().st_size
            if count > 15000 or total > 256 * 1024 * 1024:
                raise ValueError('El contexto Live supera 15 000 archivos o 256 MiB. Abre la carpeta del programa o configura una tarea específica.')
            output = directory / relative; output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, output)
    shadow = Workspace(directory, workspace.native); shadow.trusted = True
    shadow.python_workspace=getattr(workspace,'python_workspace',workspace)
    for name,text in sources.items():
        if obsolete():raise Superseded()
        count+=1;total+=len(text.encode('utf-8'))
        if count>15000 or total>256*1024*1024:raise ValueError('El contexto Live supera 15 000 archivos o 256 MiB.')
        file=shadow.resolve(name,must_exist=False);file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(text,encoding='utf-8',newline='')
    return shadow

def prepare(runtimes, workspace, path):
    """Return separate validation and execution commands. A compiler runs only once."""
    lang = language(path,runtimes.config['languages'])
    if not lang: raise ValueError('No hay adaptador Lantern para este archivo.')
    profile = runtimes.config['languages'].get(lang, {})
    remote = getattr(runtimes,'execution',None)
    if remote and remote.selected(workspace)['kind']!='local':
        plan = runtimes.plan(workspace,path)
        if lang in ('python','javascript','bash') or profile.get('run') and not profile.get('build'):
            checks=runtimes.plan(workspace,path,check=True)['commands'];commands=plan['commands']
        elif lang=='nc' and Path(path).suffix.lower() not in ('.n','.nc'):
            checks=runtimes.plan(workspace,path,check=True)['commands'];commands=plan['commands']
        else:checks=plan['commands'][:-1];commands=plan['commands'][-1:]
        return {**plan,'checks':checks,'commands':commands,'custom':True,'lensMode':'cooperative','adapter':lang,'preview':False}
    if profile.get('run') or profile.get('build'):
        if not (profile.get('check') or profile.get('build')):
            raise ValueError('El adaptador personalizado necesita check o build para validar el buffer antes de ejecutarlo.')
        plan = runtimes.plan(workspace, path)
        checks = runtimes.plan(workspace, path, check=True)['commands']
        commands = plan['commands'][-1:]
    elif lang == 'python':
        ast.parse(workspace.resolve(path).read_text(encoding='utf-8'), filename=path)
        plan = runtimes.plan(workspace, path); checks = []; commands = plan['commands']
    elif lang in ('javascript', 'typescript'):
        plan = runtimes.plan(workspace, path)
        checks = runtimes.plan(workspace, path, check=True)['commands']; commands = plan['commands']
    elif lang in ('html', 'css'):
        plan = runtimes.plan(workspace, path); checks = []; commands = []
    elif lang == 'nc':
        from .nc_project_bridge import has_project_imports
        if Path(path).suffix.lower() in ('.n','.nc') and has_project_imports(workspace.resolve(path)):
            plan=runtimes.plan(workspace,path);checks=[];commands=plan['commands']
        elif Path(path).suffix.lower() in ('.n', '.nc'):
            plan = runtimes.plan(workspace, path, debug=True); checks = plan['commands']; commands = [[str(plan['target'])]]
        else:
            plan = runtimes.plan(workspace, path); checks = runtimes.plan(workspace, path, check=True)['commands']; commands = plan['commands']
    else:
        plan = runtimes.plan(workspace, path)
        checks = plan['commands'][:-1]; commands = plan['commands'][-1:]
        if not checks: raise ValueError('El adaptador no proporciona una fase de compilación.')
    return {**plan, 'checks': checks, 'commands': commands, 'custom': bool(profile.get('run') or profile.get('build')),
            'lensMode': 'automatic' if lang == 'python' else 'cooperative',
            'adapter': lang, 'preview': plan.get('preview', False)}

def runtime_commands(plan, checkpoint, lens):
    commands = plan['commands']
    if plan.get('custom'): return commands
    if plan['language'] == 'python':
        prefix=commands[0][:-1]
        commands = [[sys.executable,'--lantern-child',str(plan['file']),str(checkpoint)]] if '--python-child' in prefix else [[*prefix,str(Path(__file__).with_name('lantern_memory.py')),str(plan['file']),str(checkpoint)]]
    elif plan['language'] in ('javascript', 'typescript') and commands and Path(commands[0][0]).stem.lower() == 'node':
        commands = [[commands[0][0], '--require', str(Path(__file__).with_name('lantern_memory.cjs')), *commands[0][1:]]]
    return commands
