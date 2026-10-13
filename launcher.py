"""Stable Windows entry point: installed previews keep separate live payloads."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DIRECTORY=re.compile(r'app-(\d+)\.(\d+)\.(\d+)-R(\d+)\Z')


def resolve_launch(root):
    root=Path(root).resolve()
    def candidate(name):
        if not isinstance(name,str) or not DIRECTORY.fullmatch(name):return None
        folder=root/name;executable=folder/'zenit.exe'
        if folder.is_symlink() or folder.resolve().parent!=root or executable.is_symlink() or not executable.is_file():return None
        return executable
    try:
        selected=candidate(json.loads((root/'installation.json').read_text(encoding='utf-8'))['directory'])
        if selected:return selected
    except (OSError,ValueError,KeyError,TypeError):pass
    versions=sorted((p.name for p in root.iterdir() if DIRECTORY.fullmatch(p.name)),key=lambda n:tuple(map(int,DIRECTORY.fullmatch(n).groups())),reverse=True)
    for name in versions:
        if selected:=candidate(name):return selected
    raise FileNotFoundError('No se encuentra una instalación completa de Zénit. Ejecuta de nuevo el instalador.')


def main():
    root=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    try:
        executable=resolve_launch(root)
        subprocess.Popen([str(executable),*sys.argv[1:]],cwd=executable.parent,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except (OSError,ValueError) as error:
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error),'Zénit · apertura',0x10)
        elif sys.stderr:print(error,file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
