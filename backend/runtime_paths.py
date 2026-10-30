"""Detect SDKs without changing the user's PATH or invoking rustup installers."""
import os
from pathlib import Path
import shutil

def windows_qemu_roots():
    """Known installer locations, read afresh after an external installation."""
    roots=[Path(os.environ.get('ProgramFiles','C:/Program Files'))/'qemu',
           Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'qemu',
           Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'Programs/qemu']
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
                for key,value in [(r'SOFTWARE\QEMU','Install_Dir'),(r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\qemu','InstallLocation'),(r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\qemu-system-x86_64.exe','Path')]:
                    try:
                        with winreg.OpenKey(hive,key,0,winreg.KEY_READ|view) as opened:
                            location,kind=winreg.QueryValueEx(opened,value)
                            if kind in (winreg.REG_SZ,winreg.REG_EXPAND_SZ) and isinstance(location,str):roots.append(Path(os.path.expandvars(location.strip('"'))))
                    except OSError:pass
    except ImportError:pass
    return roots

def find_tool(name, configured=None):
    explicit=(configured or {}).get(name)
    if explicit:
        path=Path(explicit).expanduser()
        return str(path) if path.is_file() else shutil.which(explicit)
    from .foundation import bundled_tool
    if bundled := bundled_tool(name):return bundled
    if name in ('rustc','cargo','rust-analyzer') and os.name=='nt':
        base=Path(os.environ.get('RUSTUP_HOME',Path.home()/'.rustup'))/'toolchains'
        for channel in ('stable-x86_64-pc-windows-msvc','stable-x86_64-pc-windows-gnu'):
            file=base/channel/('bin/'+name+'.exe')
            if file.is_file():return str(file)
    if found:=shutil.which(name):return found
    if name=='dlv':
        file=Path(__file__).resolve().parents[1]/'debugger-support/delve/dlv.exe'
        if file.is_file():return str(file)
    if name=='netcoredbg':
        for file in (Path(__file__).resolve().parents[1]/'debugger-support/netcoredbg').glob('**/netcoredbg.exe'):
            return str(file)
    if os.name!='nt':return None
    suffix=name if name.endswith('.exe') else name+'.exe'
    roots=[Path(os.environ.get('ProgramFiles','C:/Program Files'))/'LLVM/bin',Path('C:/msys64/ucrt64/bin'),Path('C:/msys64/mingw64/bin'),Path('C:/Program Files/Go/bin'),Path.home()/'go/bin',Path.home()/'.cargo/bin',Path('C:/Program Files/dotnet')]
    if name.startswith('qemu-'):roots=windows_qemu_roots()+roots
    for root in roots:
        file=root/suffix
        if file.is_file():return str(file)
    return None
