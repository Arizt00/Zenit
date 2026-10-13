from pathlib import Path
ROOT=Path(SPECPATH).parent
a=Analysis([str(ROOT/'launcher.py')],pathex=[str(ROOT)],datas=[],binaries=[],hiddenimports=[],excludes=['webview','playwright','PySide6','PyQt5','PyQt6','tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='Zenit-Launcher',console=False,upx=False,strip=False,version=str(ROOT/'packaging/version.txt'),icon=str(ROOT/'web/assets/lumen.ico'))
