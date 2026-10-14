from pathlib import Path
import runpy
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
ROOT=Path(SPECPATH).parent
release=runpy.run_path(str(ROOT/'backend/version.py'))
data=[(str(ROOT/'web'),'web')]+collect_data_files('webview')
a=Analysis([str(ROOT/'installer.py')],pathex=[str(ROOT)],datas=data,binaries=[],hiddenimports=collect_submodules('webview'),excludes=['playwright','tkinter','PySide6','PyQt5','PyQt6'],noarchive=False)
# The application and toolchains are already complete packages. Preserve their
# bytes as payload data; analyzing their DLLs again can collect unrelated host
# libraries and needlessly scan tens of thousands of compiler files.
a.datas.extend((name,str(ROOT/'dist'/name),'DATA') for name in ('Uninstall-Zenit.exe','Zenit-Launcher.exe'))
payload=ROOT/'dist/Zenit'
a.datas.extend(('payload/'+file.relative_to(payload).as_posix(),str(file),'DATA') for file in sorted(payload.rglob('*')) if file.is_file())
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name=f"Zenit-{release['VERSION']}-R{release['REVISION']}-Windows-Setup",console=False,upx=False,strip=False,version=str(ROOT/'packaging/version.txt'),icon=str(ROOT/'web/assets/lumen.ico') if (ROOT/'web/assets/lumen.ico').exists() else None)
