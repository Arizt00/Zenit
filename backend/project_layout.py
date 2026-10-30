"""Resolve language project roots and keep generated files out of source folders."""
import hashlib
import json
from pathlib import Path
import re
from .preferences import atomic_json

MARKERS = {'c': ('CMakeLists.txt',), 'cpp': ('CMakeLists.txt',), 'asm': ('CMakeLists.txt',),
           'java': ('pom.xml', 'build.gradle', 'build.gradle.kts'), 'python': ('pyproject.toml', 'setup.cfg'),
           'rust': ('Cargo.toml',), 'nc': ('ncc.package.json',), 'go': ('go.mod',),
           'javascript': ('package.json',), 'typescript': ('package.json',), 'csharp': ()}


def project_info(ws, file, language):
    """Use a matching Zénit descriptor first; do not infer targets from filenames."""
    parents=[folder for folder in (file.parent, *file.parent.parents) if folder.is_relative_to(ws.root)]
    for folder in parents:
        marker=ws.resolve((folder/'zenit.project.json').relative_to(ws.root).as_posix(),must_exist=False)
        if not marker.is_file():continue
        if marker.stat().st_size>64000:raise ValueError('El descriptor de proyecto supera 64 kB.')
        data=json.loads(marker.read_text(encoding='utf-8'))
        if data.get('schema')!=1 or data.get('language')!=language:continue
        lists={}
        for key in ('sources','interfaces'):
            values=data.get(key,[])
            if not isinstance(values,list) or len(values)>300:raise ValueError('Lista de archivos de proyecto no válida.')
            lists[key]=[ws.resolve((folder/Path(value)).relative_to(ws.root).as_posix()) for value in values if isinstance(value,str)]
            if len(lists[key])!=len(values):raise ValueError('Ruta de proyecto no válida.')
        entry=ws.resolve((folder/Path(data['entry'])).relative_to(ws.root).as_posix())
        if file not in (*lists['sources'],*lists['interfaces'],entry):continue
        return {'root':folder,'entry':entry,'owned':True,**lists}
    for folder in parents:
        if any(ws.resolve((folder/name).relative_to(ws.root).as_posix(),must_exist=False).is_file() for name in MARKERS.get(language,())):
            return {'root':folder,'entry':file,'sources':[file],'interfaces':[],'owned':False}
    return {'root':file.parent,'entry':file,'sources':[file],'interfaces':[],'owned':False}


def build_directory(ws,file,language,info=None):
    info=info or project_info(ws,file,language)
    entry=info['entry'] if info['owned'] else file
    source=entry.relative_to(ws.root).as_posix()
    name=(re.sub(r'[^A-Za-z0-9_]', '_',entry.stem)[:48] or 'application')+'-'+hashlib.sha256(source.encode()).hexdigest()[:8]
    if hasattr(ws,'python_workspace'):
        directory=ws.private_dir('run')/name
    else:
        root=info['root']
        directory=ws.resolve((root/'build'/language/name).relative_to(ws.root).as_posix(),must_exist=False)
    directory.mkdir(parents=True,exist_ok=True)
    return directory


def interface_path(ws,file,language,info=None):
    info=info or project_info(ws,file,language)
    suffix={'c':'.h','cpp':'.hpp','asm':'.inc'}.get(language)
    if suffix is None:return None
    for candidate in info['interfaces']:
        if candidate.suffix==suffix:return candidate
    adjacent=file.with_suffix(suffix)
    if adjacent.is_file():return adjacent
    relative=file.relative_to(info['root'])
    parent=Path(*relative.parts[1:-1]) if relative.parts[0]=='src' else relative.parent
    name=(Path('include')/parent/file.with_suffix(suffix).name).as_posix()
    return ws.resolve((info['root']/name).relative_to(ws.root).as_posix(),must_exist=False)


def cmake_dependencies(folder, compile_flags, link_flags):
    """Forward exact package arguments without interpreting them as CMake code."""
    def literal(value):
        value=str(value)
        equals='='
        while ']'+equals+']' in value:equals+='='
        return '['+equals+'['+value+']'+equals+']'
    content='# Generated from the selected Zénit dependencies.\n'
    if compile_flags:content+='add_compile_options(\n  '+'\n  '.join(map(literal,compile_flags))+'\n)\n'
    # Directory link libraries are placed after object files, including static archives.
    if link_flags:content+='link_libraries(\n  '+'\n  '.join(map(literal,link_flags))+'\n)\n'
    path=folder/'zenit-dependencies.cmake'
    if not path.is_file() or path.read_text(encoding='utf-8')!=content:path.write_text(content,encoding='utf-8')
    return path


def export_layout(ws,file,language,folder,target,commands,info=None,interfaces=()):
    if hasattr(ws,'python_workspace'):return None
    info=info or project_info(ws,file,language)
    metadata={'schema':1,'language':language,'source':file.relative_to(ws.root).as_posix(),
              'project':info['root'].relative_to(ws.root).as_posix(),
              'entry':info['entry'].relative_to(ws.root).as_posix(),
              'sources':[p.relative_to(ws.root).as_posix() for p in info['sources']],
              'interfaces':[p.relative_to(ws.root).as_posix() for p in interfaces],
              'target':str(target),'commands':[list(command) for command in commands]}
    path=folder/'project.json'
    try:previous=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    except (OSError,ValueError):previous=None
    if previous!=metadata:
        atomic_json(path,metadata)
    return {'directory':folder.relative_to(ws.root).as_posix(),'descriptor':path.relative_to(ws.root).as_posix(),
            'project':metadata['project'],'interfaces':metadata['interfaces'],'language':language}
