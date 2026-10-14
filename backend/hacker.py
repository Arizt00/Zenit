"""Python buffers and GCC/GDB workflows, using Zénit's real integrated PTY."""
import os
from pathlib import Path
import sys
import tempfile
from .runtime_paths import find_tool
from .terminals import TerminalSession


class Hacker:
    def __init__(self, features):
        self.features=features;self.builds={};self.folders=[]

    def tools(self):
        return {'python':self._python_executable(),**{name:find_tool(name) for name in ('gcc','gdb')}}

    def _python_executable(self):
        from .foundation import bundled_tool
        if executable:=bundled_tool('python'):return executable
        executable=sys.executable
        if getattr(sys,'frozen',False):
            # ConPTY hosts the console helper inside Zénit; no external CMD.
            helper=Path(executable).with_name('zenit-python.exe' if os.name=='nt' else 'zenit-python')
            if helper.is_file():return str(helper)
        return executable

    def _terminal(self, argv, label, cwd, environment=None):
        manager=self.features.terminals
        if not self.features.prefs.get('security.terminals'):raise PermissionError('Activa las terminales en Ajustes.')
        with manager.lock:
            if sum(not s.closed for s in manager.sessions.values())>=6:raise ValueError('Cierra una terminal antes de abrir otra.')
            profile={'id':'hacker','label':label,'argv':argv,'kind':'hacker'}
            # GCC/GDB depend on companion DLLs next to their executables on Windows.
            from .foundation import tool_environment
            env=dict(environment or {});env['PATH']=str(Path(argv[0]).parent)+os.pathsep+tool_environment()['PATH']
            s=TerminalSession(profile,cwd,manager.project,100,26,environment=env)
            manager.sessions[s.id]=s
            return {'id':s.id,'profile':profile,'kind':s.kind}

    def start(self, ws, path, content, mode):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto para ejecutar su código.')
        project=ws.root;ws,path=self.features.execution_workspace(ws,path)
        file=ws.resolve(path)
        if not isinstance(content,str) or len(content)>2_000_000:raise ValueError('El búfer admite hasta 2 MB.')
        if mode=='file':
            from .runtimes import language
            plan=self.features.runtimes.plan(ws,path)
            if plan.get('preview'):return {'preview':self.features.preview.start(ws,path)}
            commands=plan['commands']
            if not commands:raise ValueError('No hay una orden de ejecución para este archivo.')
            label=language(path)+' · '+file.name
            if len(commands)==1:return {'terminal':self._terminal(commands[0],label,ws.root)}
            result=self.features.app.runner.start(commands[:-1],ws.root,timeout=120)
            self.builds[result['job']]={'argv':commands[-1],'workspace':ws.root,'project':project,'name':label}
            return result
        folder=Path(tempfile.mkdtemp(prefix='lumen-hacker-'));self.folders.append(folder)
        source=folder/file.name;source.write_text(content,encoding='utf-8',newline='')
        if mode=='python':
            if file.suffix.lower() not in ('.py','.pyw'):raise ValueError('Abre un archivo Python para esta acción.')
            from .foundation import python_command
            prefix=python_command(ws,self.features.runtimes.config.get('tools'))
            if '--python-child' in prefix:prefix=[self._python_executable(),'--python-child']
            argv=[*prefix,str(source)]
            return {'terminal':self._terminal(argv,'Python · '+file.name,ws.root,{'PYTHONPATH':str(file.parent),'LUMEN_SCRIPT_IMPORT_ROOT':str(file.parent)})}
        if mode!='gdb' or file.suffix.lower()!='.c':raise ValueError('GCC + GDB requiere un archivo .c.')
        tools=self.tools()
        if not tools['gcc'] or not tools['gdb']:raise FileNotFoundError('Instala GCC y GDB (MinGW/MSYS2 en Windows) y añade su carpeta bin al PATH. Zénit detecta también C:/msys64/ucrt64/bin.')
        target=folder/('program.exe' if os.name=='nt' else 'program')
        from .native_packages import native_state
        deps=native_state(ws)
        argv=[tools['gcc'],'-g3','-O0','-Wall','-Wextra','-fno-omit-frame-pointer','-iquote',str(file.parent),*deps.get('cCompile',deps['compile']),str(source),*deps['link'],'-o',str(target)]
        result=self.features.app.runner.start([argv],ws.root,timeout=120)
        self.builds[result['job']]={'target':target,'gdb':tools['gdb'],'workspace':ws.root,'project':project,'source':source,'name':file.name}
        return {**result,'flags':argv[1:6]}

    def attach(self, ws, key):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto.')
        build=self.builds.get(key);job=self.features.app.runner.jobs.get(key)
        if not build or build.get('project',build['workspace'])!=ws.root or not job:raise ValueError('Compilación no encontrada en este proyecto.')
        if not job.done:raise ValueError('La compilación sigue en curso.')
        if 'argv' in build:
            if job.code!=0:raise ValueError('La compilación falló. Revisa sus errores en la salida de tareas.')
            result=self._terminal(build['argv'],build['name'],build['workspace']);del self.builds[key];return result
        if job.code!=0 or not build['target'].is_file():raise ValueError('GCC no pudo compilar. Revisa sus errores en la salida de tareas.')
        result=self._terminal([build['gdb'],'--quiet','-ex','set pagination off','-ex','start','--args',str(build['target'])],'GDB · '+build['name'],ws.root)
        del self.builds[key]
        return result

    def shutdown(self):
        import shutil
        for folder in self.folders:
            target=folder.resolve()
            if target.parent==Path(tempfile.gettempdir()).resolve() and target.name.startswith('lumen-hacker-'):shutil.rmtree(target,ignore_errors=True)
        self.folders.clear();self.builds.clear()
