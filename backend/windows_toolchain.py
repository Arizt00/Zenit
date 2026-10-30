"""Select complete installed MSVC libraries for NCC's host linker only."""
import os,platform,re,subprocess
from pathlib import Path


def version(path):return tuple(int(n) for n in re.findall(r'\d+',path.name))


def complete_libraries(installation,kits):
    """An incomplete newer VS toolset must not hide a working installed one."""
    tools=Path(installation)/'VC/Tools/MSVC'
    msvc=next((p/'lib/x64' for p in sorted(tools.glob('*'),key=version,reverse=True)
               if all((p/'lib/x64'/name).is_file() for name in ('legacy_stdio_definitions.lib','msvcrt.lib','vcruntime.lib'))),None)
    sdk=next((p for p in sorted((Path(kits)/'Lib').glob('*'),key=version,reverse=True)
              if (p/'ucrt/x64/ucrt.lib').is_file() and (p/'um/x64/kernel32.lib').is_file()),None)
    return [msvc,sdk/'ucrt/x64',sdk/'um/x64'] if msvc and sdk else []


def native_environment(environment):
    env=dict(environment)
    if os.name!='nt' or platform.machine().lower() not in ('amd64','x86_64') or env.get('LIB'):return env
    base=Path(env.get('ProgramFiles(x86)','C:/Program Files (x86)'))
    finder=base/'Microsoft Visual Studio/Installer/vswhere.exe'
    if not finder.is_file():return env
    try:
        result=subprocess.run([str(finder),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not result.stdout.strip():return env
        kits=[base/'Windows Kits/10']
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Windows Kits\Installed Roots') as key:
                location,kind=winreg.QueryValueEx(key,'KitsRoot10')
                if kind in (winreg.REG_SZ,winreg.REG_EXPAND_SZ):kits.insert(0,Path(os.path.expandvars(location)))
        except OSError:pass
        paths=next((paths for root in kits if (paths:=complete_libraries(Path(result.stdout.strip()),root))),[])
        if paths:env['LIB']=';'.join(map(str,paths))
    except (OSError,subprocess.SubprocessError):pass
    return env
