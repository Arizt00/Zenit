"""Prepare a private NCC module tree and execute its explicit project pipeline."""
import argparse,json,os,re,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT))
from backend.native import NativeCore
from backend.workspace import Workspace
from backend.lantern_adapters import stage

def imports(text):
    text=re.sub(r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda match:' '*len(match[0]),text)
    groups=[part for use in re.findall(r'\buse\s*<([^>]+)>',text) for part in re.findall(r'(?:^|\|)\s*project\s*:\s*([^|]+)',use)]
    return list(dict.fromkeys(name.strip() for group in groups for name in group.split(',')
                             if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*',name.strip())))

def backend_python():
    executable=Path(sys.executable)
    if getattr(sys,'frozen',False):
        console=executable.with_name('zenit-python.exe' if os.name=='nt' else 'zenit-python')
        prefix=[str(console if console.is_file() else executable),'--python-child']
    else:prefix=[str(executable),'-u']
    return prefix

def command(compiler,root,file,mode,target):
    return [*backend_python(),str(Path(__file__)), '--workspace',str(root),'--source',file.relative_to(root).as_posix(),
            '--compiler',compiler,'--mode',mode,'--output',str(target)]

def has_project_imports(file):
    return bool(imports(file.read_text(encoding='utf-8-sig')))

def materialize_modules(workspace,directory,entry):
    """NCC resolves project units under src/. Legacy adjacent files stay intact."""
    files=[p for p in workspace.files() if Path(p).suffix.lower() in ('.n','.nc')]
    pending=[entry];visited=set()
    while pending:
        source=pending.pop()
        if source in visited:continue
        visited.add(source)
        if len(visited)>200:raise ValueError('El proyecto nC supera 200 módulos.')
        for name in imports((directory/source).read_text('utf-8-sig')):
            relative=name.replace('.','/')+'.n'
            preferred='src/'+relative
            matches=[path for path in files if path.replace('\\','/').casefold() in (preferred.casefold(),relative.casefold())]
            if preferred in matches:chosen=preferred
            elif len(matches)==1:chosen=matches[0]
            else:raise ValueError('Módulo nC ausente o ambiguo: '+name)
            destination=directory/preferred;value=(directory/chosen).read_bytes()
            if destination.exists() and destination.read_bytes()!=value:raise ValueError('Dos archivos distintos representan el módulo nC '+name)
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(value)
            pending.append(preferred)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--source',required=True)
    parser.add_argument('--compiler',required=True);parser.add_argument('--mode',choices=('check','run','build'),required=True);parser.add_argument('--output')
    args=parser.parse_args();ws=Workspace(Path(args.workspace),NativeCore(ROOT));source=ws.resolve(args.source);name=source.relative_to(ws.root).as_posix()
    if args.mode=='build' and not args.output:raise ValueError('Falta el destino del enlace NCC.')
    from backend.windows_toolchain import native_environment
    environment=native_environment(os.environ)
    with tempfile.TemporaryDirectory(prefix='zenit-ncc-project-',ignore_cleanup_errors=True) as temporary:
        copy=Path(temporary)/'project';stage(ws,name,source.read_text('utf-8-sig'),copy,lambda:False)
        materialize_modules(ws,copy,name)
        def run(argv,interactive=False):
            # A Windows console input handle requires its owning console. The
            # no-window flag detaches NCC from ConPTY: prompts still print, but
            # ReadConsole/input can never receive the user's keys. Inherit the
            # existing PTY console only for execution; no extra window is made.
            # Preparation must not consume input intended for the program.
            console_input=interactive and sys.stdin is not None and sys.stdin.isatty()
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' and not console_input else 0
            process=subprocess.Popen(argv,cwd=copy,env=environment,stdin=sys.stdin if interactive else subprocess.DEVNULL,
                                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=flags)
            try:
                while block:=process.stdout.read1(16384):sys.stdout.buffer.write(block);sys.stdout.buffer.flush()
                code=process.wait()
            finally:process.stdout.close()
            if code:raise SystemExit(code)
        run([args.compiler,'project','sync',str(copy),'--main',name])
        run([args.compiler,'project','check',str(copy),'--main',name])
        if args.mode=='run':
            print('Zénit · ejecución de proyecto mediante NCC; el compilador selecciona el motor.',flush=True)
            run([args.compiler,'run',str(copy/name)],interactive=True)
        elif args.mode=='build':
            target=Path(args.output).resolve()
            if not target.is_relative_to(ws.root):raise ValueError('El ejecutable debe permanecer en el proyecto.')
            target.parent.mkdir(parents=True,exist_ok=True)
            run([args.compiler,'project','link',str(copy),'--main',name,'--out',str(target)])

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    try:main()
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr,flush=True);sys.exit(1)
