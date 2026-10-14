"""Runs under the shipped CPython; Conan recipes stay in a project-private folder."""
import json
import os
from pathlib import Path
import subprocess
import sys

RECIPE='''from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain
from conan.tools.files import save
import json, os
class ZenitDependencies(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    default_options = {"*:shared": False}
    requires = REQUIRES
    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        compile_flags, c_flags, cpp_flags, link_flags, packages = [], [], [], [], []
        for dep in self.dependencies.host.values():
            info = dep.cpp_info.aggregated_components()
            compile_flags += ["-I" + p for p in info.includedirs] + ["-D" + d for d in info.defines]
            c_flags += list(info.cflags)
            cpp_flags += list(info.cxxflags)
            link_flags += ["-L" + p for p in info.libdirs]
            link_flags += ["-l" + lib for lib in info.libs] + ["-l" + lib for lib in info.system_libs]
            link_flags += list(info.exelinkflags)
            packages.append({"name": str(dep.ref), "folder": dep.package_folder})
        save(self, os.path.join(self.generators_folder, "resolved.json"), json.dumps({"compile": list(dict.fromkeys(compile_flags)), "cCompile": list(dict.fromkeys(compile_flags+c_flags)), "cppCompile": list(dict.fromkeys(compile_flags+cpp_flags)), "link": link_flags, "packages": packages}))
'''

def main():
    request=Path(sys.argv[1]).resolve();data=json.loads(request.read_text(encoding='utf-8'));folder=request.parent
    workspace=Path(data['workspace']).resolve()
    if folder!=workspace/'.lumen/dependencies':raise ValueError('Invalid dependency directory.')
    env={**os.environ,'CONAN_HOME':str(folder/'cache'),'PYTHONNOUSERSITE':'1'}
    tools=data['tools'];env['PATH']=os.pathsep.join(dict.fromkeys(str(Path(x).parent) for x in tools.values()))+os.pathsep+env.get('PATH','')
    version=subprocess.check_output([tools['gcc'],'-dumpversion'],env=env,text=True).strip().split('.')[0]
    profile=folder/'profile';profile.write_text('[settings]\nos='+('Windows' if os.name=='nt' else 'Linux')+'\narch=x86_64\ncompiler=gcc\ncompiler.version='+version+'\ncompiler.libcxx=libstdc++11\ncompiler.cppstd=17\nbuild_type=Release\n[conf]\ntools.cmake.cmaketoolchain:generator=Ninja\ntools.build:compiler_executables='+json.dumps({'c':tools['gcc'],'cpp':tools['g++']})+'\ntools.build:jobs=4\n',encoding='utf-8')
    recipe=folder/'conanfile.py';recipe.write_text(RECIPE.replace('REQUIRES',repr(tuple(data['requires']))),encoding='utf-8')
    output=folder/'generated';output.mkdir(exist_ok=True)
    command=[sys.executable,'-I','-c','from conans.conan import run; run()','install',str(recipe),'-of',str(output),'-pr:h',str(profile),'-pr:b',str(profile),'--build=missing']
    print('Resolving '+(', '.join(data['requires']) or 'an empty dependency set'),flush=True)
    result=subprocess.run(command,env=env)
    if result.returncode:return result.returncode
    resolved=json.loads((output/'resolved.json').read_text(encoding='utf-8'));resolved['requires']=data['requires'];resolved['generatorDirectory']=str(output)
    # Commit metadata only after the resolver and all builds succeed.
    candidate=folder/'active.next.json';candidate.write_text(json.dumps(resolved,indent=2),encoding='utf-8');candidate.replace(folder/'active.json')
    print('Libraries, include paths and linker flags are ready for Run, Forge, Lantern and Debug.',flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
