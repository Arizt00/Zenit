"""Bundled SDK discovery. Project interpreters stay separate from the IDE runtime."""
import json
import os
from pathlib import Path
import sys
from functools import lru_cache

_additional_roots=()
def set_sdk_roots(paths):
    global _additional_roots
    _additional_roots=tuple(Path(p).resolve() for p in paths)
    _read_index.cache_clear()

@lru_cache(maxsize=16)
def _read_index(path,mtime,size):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema')!=1:raise ValueError('Índice SDK desconocido.')
    if not isinstance(data.get('tools',{}),dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in data.get('tools',{}).items()):raise ValueError('Herramientas SDK no válidas.')
    if not isinstance(data.get('components',[]),list) or any(not isinstance(c,dict) or not isinstance(c.get('id'),str) for c in data.get('components',[])):raise ValueError('Componentes SDK no válidos.')
    return data

def read_index(root):
    path=root/'tool-index.json';stat=path.stat()
    if stat.st_size>2_000_000:raise ValueError('Índice SDK demasiado grande.')
    return _read_index(str(path),stat.st_mtime_ns,stat.st_size)

C_STANDARDS = ('c89', 'c90', 'c99', 'c11', 'c17', 'c23', 'gnu89', 'gnu99', 'gnu11', 'gnu17', 'gnu23')
CPP_STANDARDS = ('c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23', 'c++26')
ARCHITECTURES = ('x86', 'x86_64', 'arm', 'arm64', 'riscv32', 'riscv64', 'mips')

def roots():
    candidates = list(_additional_roots)
    if os.environ.get('ZENIT_SDK_ROOT'):
        candidates.append(Path(os.environ['ZENIT_SDK_ROOT']))
    if getattr(sys, 'frozen', False):
        candidates.extend((Path(sys.executable).parent / 'sdk/foundation', Path(getattr(sys, '_MEIPASS', '.')) / 'sdk/foundation'))
        candidates.append(Path(sys.executable).parent.parent / 'sdk/foundation')
    candidates.append(Path(__file__).resolve().parents[1] / 'sdk/foundation')
    return candidates

def inventory():
    for root in roots():
        try:
            data = read_index(root)
            if data.get('schema') == 1:
                return root.resolve(), data
        except (OSError, ValueError):
            pass
    return None, {'schema': 1, 'tools': {}, 'components': []}

def bundled_tool(name):
    for root in roots():
        try:data=read_index(root)
        except (OSError,ValueError):continue
        relative=data.get('tools',{}).get(name)
        if data.get('schema')!=1 or not isinstance(relative,str):continue
        root=root.resolve();candidate=(root/relative).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():return str(candidate)
    return None

def python_command(workspace=None,configured=None):
    if workspace is not None:
        from .python_packages import environment_python
        folder,python=environment_python(getattr(workspace,'python_workspace',workspace))
        if python.is_file() and (folder/'pyvenv.cfg').is_file():return [str(python),'-u']
    if configured:
        from .runtime_paths import find_tool
        if explicit:=find_tool('python',configured):return [explicit,'-u']
    executable = bundled_tool('python')
    if executable:
        return [executable, '-u']
    return [sys.executable, '--python-child'] if getattr(sys, 'frozen', False) else [sys.executable, '-u']

def tool_environment():
    bins = []
    for root in roots():
        try:data=read_index(root)
        except (OSError,ValueError):continue
        root=root.resolve()
        for relative in data.get('tools',{}).values():
            if isinstance(relative,str):
                directory=(root/relative).resolve().parent
                if directory.is_relative_to(root) and directory.is_dir() and str(directory) not in bins:bins.append(str(directory))
    environment = {'PATH': os.pathsep.join([*bins, os.environ.get('PATH', '')]), 'PYTHONNOUSERSITE': '1'}
    java = bundled_tool('java')
    if java:
        environment['JAVA_HOME'] = str(Path(java).parents[1])
    return environment

def status():
    from .runtime_paths import find_tool
    root, data = inventory()
    names = ('python', 'gcc', 'g++', 'clang', 'java', 'javac', 'bash', 'ncc', 'node', 'docker', 'qemu-system-x86_64', 'mvn', 'gradle')
    return {'bundle': bool(root), 'directory': str(root) if root else None,
            'components': data.get('components', []),
            'tools': [{'id': name, 'path': find_tool(name), 'bundled': bool(bundled_tool(name))} for name in names],
            'architectures': list(ARCHITECTURES), 'standards': {'c': list(C_STANDARDS), 'cpp': list(CPP_STANDARDS)},
            'dependencyPolicy': 'Bibliotecas estándar incluidas; paquetes de proyecto en venv, Maven/Gradle o el gestor de su lenguaje.'}
