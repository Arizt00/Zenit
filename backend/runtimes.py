"""Language-aware build/run plans and explicit local debugger configuration."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import xml.sax.saxutils
from .preferences import atomic_json
from .toolchains import validate_argv
from .runtime_paths import find_tool
from .project_layout import project_info, build_directory, interface_path, export_layout

SUFFIXES={'python':('.py','.pyw'),'javascript':('.js','.mjs','.cjs'),'typescript':('.ts',),
 'asm':('.s','.asm'),'bash':('.sh','.bash'),'c':('.c',),'cpp':('.cpp','.cc','.cxx'),'rust':('.rs',),'go':('.go',),'java':('.java',),
 'csharp':('.cs',),'html':('.html','.htm','.htmll'),'css':('.css',),'nc':('.n','.nc','.nm','.ncp','.nb','.nbb')}
TOOLS={'asm':('gcc','clang'),'bash':('bash',),'python':(),'javascript':('node',),'typescript':('node',),'c':('gcc','clang'),'cpp':('g++','clang++'),
 'rust':('rustc',),'go':('go',),'java':('javac','java'),'csharp':('dotnet',),'html':(),'css':(),'nc':('ncc',)}
LABELS={'asm':'ASM · ensamblador','bash':'Bash','python':'Python','javascript':'JavaScript','typescript':'TypeScript','c':'C','cpp':'C++','rust':'Rust','go':'Go','java':'Java','csharp':'C#','html':'HTML','css':'CSS','nc':'nC'}

def language(path,profiles=None):
    suffix=Path(path).suffix.lower()
    return next((name for name,suffixes in SUFFIXES.items() if suffix in suffixes),None) or next((name for name,profile in (profiles or {}).items() if suffix in profile.get('extensions',[])),None)

class Runtimes:
    def __init__(self,prefs):
        self.path=prefs.directory/'languages.json';self.config={'languages':{},'tools':{}}
        defaults=Path(__file__).resolve().parents[1]/'config/runtime-defaults.json'
        if defaults.is_file():
            try:self.config=self.validate(json.loads(defaults.read_text(encoding='utf-8')))
            except (ValueError,TypeError,OSError):pass
        local=defaults.with_name('runtime-local.json')
        if local.is_file() and not getattr(sys,'frozen',False):
            try:self.config=self.validate(json.loads(local.read_text(encoding='utf-8')))
            except (ValueError,TypeError,OSError):pass
        if self.path.is_file():
            try:self.config=self.validate(json.loads(self.path.read_text(encoding='utf-8')))
            except (ValueError,TypeError,OSError):pass
    def validate(self,data):
        if not isinstance(data,dict) or not isinstance(data.get('languages'),dict):raise ValueError('Usa un objeto languages.')
        out={'languages':{},'tools':{}}
        for name,path in data.get('tools',{}).items():
            if name not in ('python','bash','ncc','node','nasm','clang','clang++','gcc','g++','cmake','ninja','rustc','cargo','go','javac','java','dotnet','lldb-dap','lldb-vscode','dlv','netcoredbg'):raise ValueError('Herramienta desconocida: '+str(name))
            if not isinstance(path,str) or not path or len(path)>4096 or '\x00' in path:raise ValueError('Ruta no válida.')
            out['tools'][name]=path
        for name,profile in data['languages'].items():
            if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',name) or not isinstance(profile,dict):raise ValueError('Lenguaje o perfil no válido.')
            item={}
            if 'extensions' in profile:
                suffixes=profile['extensions']
                if not isinstance(suffixes,list) or not 1<=len(suffixes)<=10 or any(not isinstance(s,str) or not re.fullmatch(r'\.[a-z0-9_+-]{1,16}',s) for s in suffixes):raise ValueError('Define entre una y diez extensiones como .rb o .lua.')
                if name not in SUFFIXES and any(s in known for known in SUFFIXES.values() for s in suffixes):raise ValueError('No sustituyas extensiones de lenguajes integrados.')
                item['extensions']=list(dict.fromkeys(suffixes))
            if name not in SUFFIXES and (not item.get('extensions') or not (profile.get('run') or profile.get('build'))):raise ValueError('Un lenguaje adicional necesita extensions y una orden run o build.')
            if 'standard' in profile:
                from .foundation import C_STANDARDS, CPP_STANDARDS
                choices=C_STANDARDS if name=='c' else CPP_STANDARDS if name=='cpp' else ()
                if profile['standard'] not in choices:raise ValueError('Estándar no válido para '+name)
                item['standard']=profile['standard']
            for key in ('run','build','check'):
                if key in profile:item[key]=validate_argv(profile[key])
            if 'debug' in profile:
                debug=profile['debug']
                if not isinstance(debug,dict):raise ValueError('Configuración debug no válida.')
                adapter=validate_argv(debug.get('adapter'));launch=debug.get('launch',{})
                if not isinstance(launch,dict) or len(json.dumps(launch))>32000:raise ValueError('Argumentos DAP no válidos.')
                transport=debug.get('transport','stdio')
                if transport not in ('stdio','tcp'):raise ValueError('DAP usa stdio o tcp local.')
                item['debug']={'adapter':adapter,'launch':copy.deepcopy(launch),'transport':transport}
            out['languages'][name]=item
        owners={}
        for name,profile in out['languages'].items():
            for suffix in profile.get('extensions',[]):
                if suffix in owners and owners[suffix]!=name:raise ValueError('La extensión '+suffix+' pertenece a dos perfiles.')
                owners[suffix]=name
        return out
    def save(self,data):
        result=self.validate(data);atomic_json(self.path,result);self.config=result;return copy.deepcopy(result)
    def expand(self,value,ws,file,target,port=0):
        substitutions={'${workspaceFolder}':str(ws.root),'${file}':str(file),'${fileDirname}':str(file.parent),
            '${fileBasenameNoExtension}':file.stem,'${target}':str(target),'${port}':str(port)}
        if isinstance(value,str):
            for key,item in substitutions.items():value=value.replace(key,item)
            return value
        if isinstance(value,list):return [self.expand(x,ws,file,target,port) for x in value]
        if isinstance(value,dict):return {k:self.expand(v,ws,file,target,port) for k,v in value.items()}
        return value
    def executable(self,*names):
        for name in names:
            if found:=find_tool(name,self.config.get('tools')):return found
        raise ValueError('Falta '+ ' / '.join(names)+'. Instala su SDK o configura la ruta en Lenguajes y depuradores.')
    def plan(self,ws,path,check=False,debug=False,build_only=False):
        if not ws.trusted:raise PermissionError('Autoriza el proyecto antes de ejecutar código.')
        execution=getattr(self,'execution',None)
        if execution:
            if debug:execution.require_local(ws,'La depuración DAP')
            remote=execution.plan(ws,path,check,build_only=build_only)
            if remote is not None:return remote
        file=ws.resolve(path);lang=language(path,self.config['languages'])
        if not lang:raise ValueError('Configura el lenguaje y sus extensiones en SDK y lenguajes.')
        info=project_info(ws,file,lang)
        folder=build_directory(ws,file,lang,info)
        target=folder/(file.stem+('.exe' if os.name=='nt' else ''))
        interfaces=list(info['interfaces'])
        custom=self.config['languages'].get(lang,{})
        if custom.get('run') or custom.get('build'):
            commands=[]
            if check or build_only:
                step=custom.get('check') if check else None
                step=step or custom.get('build')
                if not step:raise ValueError('Este perfil necesita una orden '+('check o build' if check else 'build')+' para esta acción.')
                commands=[step]
            else:
                if custom.get('build'):commands.append(custom['build'])
                if not check and not debug:commands.append(custom.get('run',[str(target)]))
            return {'language':lang,'commands':self.expand(commands,ws,file,target),'target':target,'file':file,'cwd':ws.root,'buildOnly':build_only}
        commands=[]
        if lang=='python':
            if check:compile(file.read_bytes(),str(file),'exec')
            else:
                from .foundation import python_command
                from .workspace import Workspace
                scope=Workspace(info['root'],ws.native) if info['root']!=ws.root and not hasattr(ws,'python_workspace') else ws
                if scope is not ws:
                    from .python_packages import environment_python
                    if not environment_python(scope)[1].is_file():scope=ws
                python=python_command(scope,self.config.get('tools'))
                if build_only:
                    target=folder/(file.stem+'.pyc')
                    commands=[[*python,'-c','import py_compile,sys; py_compile.compile(sys.argv[1],cfile=sys.argv[2],doraise=True)',str(file),str(target)]]
                elif not debug:
                    target=file
                    commands=[[*python,'-X','pycache_prefix='+str(folder/'cache'),str(file)]]
        elif lang=='bash':
            commands=[[self.executable('bash'),*(['-n'] if check else []),str(file)]]
        elif lang in ('javascript','typescript'):
            node=self.executable('node');commands=[] if debug else [[node,*(['--check'] if check else []),str(file)]]
        elif lang in ('html','css'):
            if check and lang=='html':
                from html.parser import HTMLParser
                HTMLParser().feed(file.read_text(encoding='utf-8-sig'))
            return {'language':lang,'commands':[],'target':file,'file':file,'cwd':ws.root,'preview':not check}
        elif lang=='asm':
            source=file.read_text(encoding='utf-8-sig')
            if re.search(r'(?m)^\s*(?:ecall\b|(?:li|la|addi)\s+(?:a[0-7]|t[0-6]|zero)\b|[a-z]+\s+\$(?:a[0-3]|v[01]|t[0-9]|zero)\b)',source):
                raise ValueError('Este ASM usa registros o servicios RISC-V/MIPS. Abre Laboratorio ASM y selecciona RARS o MARS para simularlo, o compila con la toolchain de su máquina virtual. No es ASM nativo del equipo.')
            from .native_packages import native_state
            deps=native_state(ws)
            if file.suffix.lower()=='.asm':
                from .nasm import target_system
                system=target_system(source);host='windows' if os.name=='nt' else 'linux' if sys.platform.startswith('linux') else 'macos'
                bits=32 if re.search(r'(?im)^\s*\[?bits\s+32\b',source) else 64
                if not check and system!=host:raise ValueError('Este archivo NASM tiene destino '+system.title()+', pero este equipo usa '+host.title()+'. Selecciona NASM + Unicorn y ese destino en Laboratorio ASM, o ejecútalo en '+('Linux/WSL o una máquina virtual Linux.' if system=='linux' else 'una estación o máquina virtual Windows.'))
                if not check and bits==32:raise ValueError('El ejecutor nativo incluido es de 64 bits. Simula NASM x86 de 32 bits en el laboratorio o configura su toolchain de 32 bits.')
                nasm=self.executable('nasm');obj=folder/(file.stem+('.obj' if system=='windows' else '.o'))
                include=interface_path(ws,file,lang,info)
                if include and not check and not hasattr(ws,'python_workspace'):
                    include.parent.mkdir(parents=True,exist_ok=True)
                    try:
                        with include.open('x',encoding='utf-8') as stream:stream.write('; NASM interface: constants, macros and shared declarations.\n')
                    except FileExistsError:pass
                    if include not in interfaces:interfaces.append(include)
                commands=[[nasm,'-f',('win' if system=='windows' else 'elf')+str(bits),'-I',str(file.parent)+os.sep,
                           '-I',str(include.parent if include else info['root']/'include')+os.sep,str(file),'-o',str(obj)]]
                if not check:
                    compiler=self.executable('gcc','clang');start=re.search(r'(?im)^\s*(?:global|GLOBAL)\s+_start\b',source)
                    flags=['-nostartfiles','-Wl,-e,_start','-lkernel32'] if start and system=='windows' else ['-nostdlib','-no-pie','-Wl,-e,_start'] if start else []
                    commands.append([compiler,str(obj),*flags,*deps['link'],'-o',str(target)])
            else:commands=[[self.executable('gcc','clang'),*(['-g'] if debug else []),*deps['compile'],str(file),*deps['link'],'-o',str(target)]]
            if not check and not debug:commands.append([str(target)])
        elif lang in ('c','cpp'):
            from .native_packages import native_state
            deps=native_state(ws)
            compiler=self.executable(*TOOLS[lang]);standard='-std='+custom.get('standard','c++20' if info['owned'] and lang=='cpp' else 'c++17' if lang=='cpp' else 'c17' if info['owned'] else 'c11')
            include=interface_path(ws,file,lang,info)
            include_args=['-I',str(include.parent),'-I',str(info['root']/'include')]
            commands=[[compiler,standard,'-Wall','-Wextra',*include_args,'-I',str(Path(__file__).resolve().parents[1]/'debugger-support/lantern'),*deps.get('cppCompile' if lang=='cpp' else 'cCompile',deps['compile']),*(['-g','-O0'] if debug else []),*(['-fsyntax-only'] if check else ['-save-temps=obj']),*[str(source) for source in info['sources']],*([] if check else [*deps['link'],'-o',str(target)])]]
            if info['owned'] and not check and not hasattr(ws,'python_workspace'):
                cmake=find_tool('cmake',self.config.get('tools'));ninja=find_tool('ninja',self.config.get('tools'))
                if not cmake or not ninja:raise ValueError('Este proyecto usa CMake + Ninja. Prepara ambas herramientas en el SDK.')
                variable='CMAKE_CXX_COMPILER' if lang=='cpp' else 'CMAKE_C_COMPILER'
                from .project_layout import cmake_dependencies
                packages=cmake_dependencies(folder,['-Wall','-Wextra',*deps.get('cppCompile' if lang=='cpp' else 'cCompile',deps['compile'])],deps['link'])
                standard_name='CMAKE_CXX_STANDARD' if lang=='cpp' else 'CMAKE_C_STANDARD'
                standard_number=re.search(r'\d+$',standard).group()
                target=folder/'bin'/('zenit_app'+('.exe' if os.name=='nt' else ''))
                commands=[[cmake,'-S',str(info['root']),'-B',str(folder),'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+ninja,
                           '-D'+variable+'='+compiler,'-D'+standard_name+'='+standard_number,'-DCMAKE_PROJECT_INCLUDE='+packages.as_posix(),
                           '-DCMAKE_BUILD_TYPE=Debug','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'],
                          [cmake,'--build',str(folder),'--target','zenit_app','--parallel','2']]
            if not check and not debug:commands.append([str(target)])
        elif lang=='rust':
            manifest=info['root']/'Cargo.toml'
            if manifest.is_file() and not hasattr(ws,'python_workspace'):
                import tomllib
                data=tomllib.loads(manifest.read_text(encoding='utf-8'));package=data.get('package',{})
                bins=[(item.get('name'),(info['root']/item.get('path','src/main.rs')).resolve()) for item in data.get('bin',[]) if item.get('name')]
                if not bins and (info['root']/'src/main.rs').is_file():bins=[(package.get('name'),info['root']/'src/main.rs')]
                selected=next((name for name,source in bins if source==file),None) or package.get('default-run') or (bins[0][0] if len(bins)==1 else None)
                if not selected:raise ValueError('Selecciona un binario de Cargo o configura default-run en Cargo.toml.')
                cargo=find_tool('cargo',self.config.get('tools'));rustc=self.executable('rustc')
                if not cargo:raise ValueError('Este proyecto necesita Cargo. Prepara el SDK de Rust.')
                target=folder/'cargo-target/debug'/(selected+('.exe' if os.name=='nt' else ''))
                commands=[[cargo,'check' if check else 'build','--manifest-path',str(manifest),'--bin',selected,
                           '--target-dir',str(folder/'cargo-target'),'--config','build.rustc='+json.dumps(rustc),'--color','never']]
            else:
                compiler=self.executable('rustc');commands=[[compiler,'--edition=2021',*(['-g','-C','opt-level=0'] if debug else []),*(['--emit=metadata'] if check else []),str(file),'-o',str(target)]]
            if not check and not debug:commands.append([str(target)])
        elif lang=='go':
            go=self.executable('go');commands=[[go,'build',*(['-gcflags=all=-N -l'] if debug else []),'-o',str(target),str(file)]]
            if not check and not debug:commands.append([str(target)])
        elif lang=='java':
            javac=self.executable('javac');java=self.executable('java')
            classes=folder/'classes';classes.mkdir(exist_ok=True)
            source_root=info['root']/'src/main/java'
            commands=[[javac,'-J-Dfile.encoding=UTF-8','-J-Dstdout.encoding=UTF-8','-J-Dstderr.encoding=UTF-8','-g','-encoding','UTF-8',
                       '-sourcepath',os.pathsep.join([str(source_root),str(file.parent)]),'-d',str(classes),str(file)]]
            package=re.search(r'^\s*package\s+([\w.]+)\s*;',file.read_text(encoding='utf-8-sig'),re.M);main=(package.group(1)+'.' if package else '')+file.stem
            target=classes
            if not check and not debug:commands.append([java,'-Dfile.encoding=UTF-8','-Dstdin.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-cp',str(classes),main])
        elif lang=='csharp':
            if re.search(r'\b(using\s+UnityEngine|MonoBehaviour)\b',file.read_text(encoding='utf-8-sig')):raise ValueError('Este componente pertenece a Unity. Abre el proyecto en Unity o configura una tarea y su adaptador DAP de Unity.')
            dotnet=self.executable('dotnet');projects=[]
            for parent in [file.parent,*file.parents]:
                if not parent.is_relative_to(ws.root):break
                projects=list(parent.glob('*.csproj'))
                if projects:break
            if len(projects)>1:raise ValueError('Hay varios proyectos .NET. Configura el proyecto de inicio en Lenguajes y depuradores.')
            if projects:project=projects[0]
            else:
                import subprocess
                result=subprocess.run([dotnet,'--version'],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                match=re.match(r'(\d+)\.',result.stdout.strip())
                if not match:raise ValueError('El SDK .NET no está preparado: '+result.stderr[:500])
                project=folder/'LumenScript.csproj';escaped=xml.sax.saxutils.escape(str(file),{'"':'&quot;'})
                project.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net{match.group(1)}.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems><ImplicitUsings>enable</ImplicitUsings><DebugType>portable</DebugType></PropertyGroup><ItemGroup><Compile Include="{escaped}" /></ItemGroup></Project>',encoding='utf-8')
            out=folder/'bin';target=out/(project.stem+'.dll')
            commands=[[dotnet,'build',str(project),'-c','Debug','-o',str(out),'--nologo']]
            if not check and not debug:commands.append([dotnet,str(target)])
        elif lang=='nc':
            ncc=self.executable('ncc')
            from .nc_project_bridge import has_project_imports,command as project_command
            manifest=ws.resolve((info['root']/'ncc.package.json').relative_to(ws.root).as_posix(),must_exist=False)
            package=json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() and not hasattr(ws,'python_workspace') else {}
            entry=package.get('targets',{}).get('main')
            project_mode=file.suffix.lower() in ('.n','.nc') and has_project_imports(file)
            if project_mode:commands=[project_command(ncc,info['root'],file,'check' if check else 'build' if debug or build_only else 'run',target)]
            elif entry and (info['root']/entry).resolve()==file and check:commands=[[ncc,'package','check','--path',str(info['root'])]]
            elif check:commands=[[ncc,'check',str(file)]]
            elif file.suffix.lower() in ('.n','.nc'):
                commands=[[ncc,'compiler','build-native',str(file),'--profile','debug','--out-dir',str(folder),'--out',str(target),'--no-run','--strict']]
                if not debug:commands.append([str(target)])
            elif not debug:commands=[[ncc,'run',str(file)]]
        result={'language':lang,'commands':commands,'target':target,'file':file,'cwd':ws.root}
        if lang=='nc' and project_mode:result['projectMode']='ncc-project-runtime';result['nativeLinkRequired']=bool(debug or build_only)
        if not check and lang in ('c','cpp') and commands and not info['owned']:
            from .build_reuse import BuildReuse,BuildCommands
            depfile=folder/'build-inputs.d';commands[0][1:1]=['-MD','-MF',str(depfile),'-Wl,-t']
            result['commands']=BuildCommands(commands,BuildReuse(ws,file,target,depfile,commands[0]))
        if not check and lang in ('c','cpp','rust','nc') and (lang!='nc' or file.suffix.lower() in ('.n','.nc')):
            from .native_project import prepare_native_project
            result['artifacts']=prepare_native_project(ws,file,lang,target,commands if debug or result.get('projectMode') else commands[:-1],folder,info)
            if result['artifacts'] and result['artifacts']['header']:
                header=ws.resolve(result['artifacts']['header'])
                if header not in interfaces:interfaces.append(header)
        if build_only:
            if lang!='python' and not debug and commands and not result.get('projectMode'):result['commands']=result['commands'][:-1]
            result['buildOnly']=True
        if not check:
            result['layout']=export_layout(ws,file,lang,folder,target,result['commands'],info,interfaces)
        return result
    def status(self):
        result=[]
        for name in dict.fromkeys([*SUFFIXES,*self.config['languages']]):
            custom=self.config['languages'].get(name,{})
            tools=TOOLS.get(name,())
            if custom.get('run') or custom.get('build'):
                required=list(dict.fromkeys(argv[0] for key in ('run','build','check') if (argv:=custom.get(key)) and not argv[0].startswith('${target}')))
                available=bool(required) and all(find_tool(x,self.config.get('tools')) for x in required)
            else:
                available=all(find_tool(x,self.config.get('tools')) for x in tools) if name in ('java',) else any(find_tool(x,self.config.get('tools')) for x in tools) if tools else name in SUFFIXES
            adapter='Integrado' if name in ('python','javascript','typescript') else 'Navegador' if name in ('html','css') else 'DAP configurado' if custom.get('debug') else 'Delve' if name=='go' else 'NetCoreDbg' if name=='csharp' else 'LLDB DAP' if name in ('c','cpp','rust') else 'JDI integrado' if name=='java' else 'ncc / LLDB DAP' if name=='nc' else 'Configurar DAP'
            result.append({'id':name,'name':LABELS.get(name,name),'extensions':SUFFIXES.get(name,custom.get('extensions',[])),'available':available,'tools':tools,'debugger':adapter})
        return {'languages':result,'config':copy.deepcopy(self.config)}
