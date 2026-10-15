"""Windows Installed apps registration for the per-user Zénit installation."""
from datetime import date
import os
from pathlib import Path
import subprocess

UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\LumenStudio'


def register_uninstaller(root, version):
    if os.name != 'nt':
        return
    import winreg
    root = Path(root).resolve()
    uninstaller = root / 'Uninstall-Zenit.exe'
    if not uninstaller.is_file():
        raise FileNotFoundError('The graphical uninstaller must be installed before registration.')
    # The root launcher survives upgrades; a version directory may have already
    # been removed during a failed uninstall or superseded by a newer revision.
    launcher = root / 'Zenit.exe'
    icon = launcher if launcher.is_file() else uninstaller
    values = {
        'DisplayName': 'Zénit IDE',
        'DisplayVersion': version,
        'Publisher': 'Zénit',
        'InstallLocation': str(root),
        'DisplayIcon': f'"{icon}",0',
        'UninstallString': subprocess.list2cmdline([str(uninstaller), '--target', str(root)]),
        'InstallDate': date.today().strftime('%Y%m%d'),
        'URLInfoAbout': 'https://github.com/Arizt00/Zenit',
    }
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as entry:
        for name, value in values.items():
            winreg.SetValueEx(entry, name, 0, winreg.REG_SZ, value)
        # This is an EXE installer: expose Uninstall, without advertising MSI
        # maintenance actions that the standalone application does not implement.
        for name, value in {'NoModify': 1, 'NoRepair': 1, 'NoRemove': 0, 'SystemComponent': 0}.items():
            winreg.SetValueEx(entry, name, 0, winreg.REG_DWORD, value)
