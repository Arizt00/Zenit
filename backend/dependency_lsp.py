"""Project dependency paths for real language-server sessions."""
import copy
from pathlib import Path
from .foundation import python_command, bundled_tool
from .native_packages import native_state
from .preferences import atomic_json

def configure(profile,ws):
    profile=copy.deepcopy(profile);languages=profile.get('languages',[]);argv=profile['argv'];name=Path(argv[0]).stem.lower()
    if 'python' in languages:
        python=python_command(ws)[0]
        if name in ('pylsp','python','python3') and ('pylsp' in ' '.join(argv) or profile.get('id')=='bundled-pylsp'):
            profile['argv']=[python,'-I','-m','pylsp']
            profile.setdefault('settings',{}).setdefault('pylsp',{}).setdefault('plugins',{}).setdefault('jedi',{})['environment']=python
    if name=='clangd':
        # Keep user databases authoritative; generate per-file C/C++ commands otherwise.
        explicit=any(x.startswith('--compile-commands-dir') for x in argv)
        if not explicit and not any((ws.root/p/'compile_commands.json').exists() for p in ('','build')):
            deps=native_state(ws)
            profile.setdefault('initializationOptions',{})['fallbackFlags']=deps['compile']
            commands=[]
            for relative in ws.files():
                suffix=Path(relative).suffix.lower()
                if suffix not in ('.c','.cc','.cpp','.cxx'):continue
                cpp=suffix!='.c';compiler=bundled_tool('g++' if cpp else 'gcc')
                if compiler:commands.append({'directory':str(ws.root),'file':str(ws.resolve(relative)),'arguments':[compiler,'-std=c++17' if cpp else '-std=c11',*deps.get('cppCompile' if cpp else 'cCompile',deps['compile']),'-c',str(ws.resolve(relative))]})
            if commands:
                folder=ws.private_dir('dependencies/lsp');atomic_json(folder/'compile_commands.json',commands)
                argv=[*argv,'--compile-commands-dir='+str(folder)];profile['argv']=argv
        gcc=bundled_tool('gcc');gxx=bundled_tool('g++')
        if gcc and gxx and not any(x.startswith('--query-driver') for x in argv):profile['argv']=[*argv,'--query-driver='+','.join([gcc,gxx])]
    return profile
