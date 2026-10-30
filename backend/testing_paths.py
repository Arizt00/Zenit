"""Bounded passive discovery of generated CMake directories and nC smoke entries."""
import os
from pathlib import Path
import re


def ctest_directories(ws, names):
    roots={ws.root}
    for name in names:
        if Path(name).name=='CMakeLists.txt':roots.add(ws.resolve(name).parent)
    found=set();visited=0
    for root in sorted(roots):
        for base in (root/'build',root/'.lumen/build'):
            if not base.is_dir() or base.is_symlink() or getattr(base,'is_junction',lambda:False)():continue
            for directory,dirs,files in os.walk(base,followlinks=False):
                visited+=1
                if visited>512:raise ValueError('Hay demasiados directorios de compilación; conserva sólo los destinos de pruebas necesarios.')
                folder=Path(directory);depth=len(folder.relative_to(base).parts)
                dirs[:]=[d for d in dirs if depth<4 and not (folder/d).is_symlink() and not getattr(folder/d,'is_junction',lambda:False)()]
                if 'CTestTestfile.cmake' in files:
                    marker=ws.resolve((folder/'CTestTestfile.cmake').relative_to(ws.root).as_posix())
                    found.add(marker.parent.relative_to(ws.root).as_posix())
                    # CTest traverses add_subdirectory itself. Do not offer a
                    # child as another independent suite or run it twice.
                    dirs[:]=[]
    return sorted(found)


def nc_entries(ws,names):
    entries=[]
    for name in names:
        if Path(name).suffix.lower()!='.n':continue
        path=ws.resolve(name)
        try:
            if path.stat().st_size>1_000_000:continue
            text=path.read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError):continue
        # Mask literals/comments before locating the canonical entry reference;
        # this is passive entry discovery, not a claim of an nC parser or suite.
        masked=re.sub(r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda m:re.sub(r'[^\r\n]',' ',m[0]),text)
        main=re.search(r'\bref\s+main\s*->>',masked)
        if main:entries.append({'id':name+'::main','name':Path(name).name+' · main (humo NCC)','path':name,'line':masked[:main.start()].count('\n')+1,'framework':'ncc','kind':'smoke'})
    return entries
