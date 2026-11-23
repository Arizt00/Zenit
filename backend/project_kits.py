"""Language-specific starter projects; every source and interface has its own role."""
import json


def kit(label, tools, entry, files, interfaces=(), sources=(), description=''):
    files = dict(files)
    files['.gitignore'] = 'build/\n.lumen/\n.venv/\n.pytest_cache/\n__pycache__/\n*.py[cod]\ntarget/\n.ncc/\n.idea/\n'
    files['zenit.project.json'] = json.dumps({'schema': 1, 'language': entry.rsplit('.', 1)[-1],
        'entry': entry, 'sources': list(sources or (entry,)), 'interfaces': list(interfaces)}, indent=2)+'\n'
    return {'label': label, 'tools': tools, 'entry': entry, 'files': files,
            'interfaces': list(interfaces), 'description': description}


CMAKE_PRESETS = '''{
  "version": 3,
  "configurePresets": [{"name": "debug", "generator": "Ninja", "binaryDir": "${sourceDir}/build/debug", "cacheVariables": {"CMAKE_BUILD_TYPE": "Debug", "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"}}],
  "buildPresets": [{"name": "debug", "configurePreset": "debug"}],
  "testPresets": [{"name": "debug", "configurePreset": "debug", "output": {"outputOnFailure": true}}]
}
'''

KITS = {
 'c': kit('C', ['gcc', 'cmake', 'ninja'], 'src/main.c', {
    'src/main.c': '#include <stdio.h>\n#include "app.h"\nint main(void) { printf("%d\\n", answer()); return 0; }\n',
    'src/app.c': '#include "app.h"\nint answer(void) { return 42; }\n',
    'include/app.h': '#ifndef ZENIT_APP_H\n#define ZENIT_APP_H\nint answer(void);\n#endif\n',
    'tests/test_app.c': '#include <assert.h>\n#include "app.h"\nint main(void) { assert(answer() == 42); return 0; }\n',
    'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.20)
project(zenit_project LANGUAGES C)
set(CMAKE_C_STANDARD 17 CACHE STRING "C language standard")
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
add_library(zenit_core src/app.c)
target_include_directories(zenit_core PUBLIC include)
add_executable(zenit_app src/main.c)
target_link_libraries(zenit_app PRIVATE zenit_core)
enable_testing()
add_executable(zenit_tests tests/test_app.c)
target_link_libraries(zenit_tests PRIVATE zenit_core)
add_test(NAME unit COMMAND zenit_tests)
add_test(NAME smoke COMMAND zenit_app)
set_tests_properties(smoke PROPERTIES PASS_REGULAR_EXPRESSION "42")
''',
    'CMakePresets.json': CMAKE_PRESETS,
    'README.md': '# Proyecto C\n\n`src/`: implementación. `include/app.h`: interfaz pública. `tests/`: pruebas.\n\nEn Zénit, ejecuta `src/main.c`. Se utiliza CMake + Ninja con tu compilador C.\nTambién puedes usar `cmake --preset debug`, `cmake --build --preset debug` y `ctest --preset debug`.\nLos resultados y compile_commands.json quedan en build/.\n',
 }, ['include/app.h'], ['src/main.c', 'src/app.c'], 'C17 · src/, include/, tests/, CMake y presets de compilación.'),
 'cpp': kit('C++', ['g++', 'cmake', 'ninja'], 'src/main.cpp', {
    'src/main.cpp': '#include <iostream>\n#include "app.hpp"\nint main() { std::cout << zenit::answer() << "\\n"; }\n',
    'src/app.cpp': '#include "app.hpp"\nnamespace zenit { int answer() { return 42; } }\n',
    'include/app.hpp': '#pragma once\nnamespace zenit { int answer(); }\n',
    'tests/test_app.cpp': '#include <cassert>\n#include "app.hpp"\nint main() { assert(zenit::answer() == 42); }\n',
    'CMakePresets.json': CMAKE_PRESETS,
    'README.md': '# Proyecto C++\n\n`src/`: implementación. `include/app.hpp`: interfaz pública. `tests/`: pruebas.\nEjecuta src/main.cpp en Zénit o configura y compila con el preset debug de CMake.\n`ctest --preset debug` ejecuta las pruebas. Los resultados quedan en build/.\n',
 }, ['include/app.hpp'], ['src/main.cpp', 'src/app.cpp'], 'C++20 · src/, include/, tests/, CMake y presets de compilación.'),
 'asm': kit('ASM · NASM x86-64', ['nasm', 'gcc'], 'src/main.asm', {
    'src/main.asm': 'bits 64\n%include "main.inc"\nglobal main\nsection .text\nmain:\n    mov eax, EXIT_SUCCESS\n    ret\n',
    'include/main.inc': '%ifndef ZENIT_MAIN_INC\n%define ZENIT_MAIN_INC\n%define EXIT_SUCCESS 0\n%endif\n',
    'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.20)
if(WIN32)
  set(CMAKE_ASM_NASM_OBJECT_FORMAT win64)
else()
  set(CMAKE_ASM_NASM_OBJECT_FORMAT elf64)
endif()
project(zenit_asm LANGUAGES C ASM_NASM)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
add_executable(zenit_app src/main.asm)
target_include_directories(zenit_app PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include/")
set_target_properties(zenit_app PROPERTIES LINKER_LANGUAGE C)
enable_testing()
add_test(NAME smoke COMMAND zenit_app)
''',
    'CMakePresets.json': CMAKE_PRESETS,
    'README.md': '# Proyecto NASM x86-64\n\n`src/main.asm`: instrucciones. `include/main.inc`: constantes y macros.\nZénit ensambla con NASM, enlaza para el sistema anfitrión y separa el objeto del ejecutable.\nCMake incluye una prueba de salida correcta. RISC-V y MIPS se trabajan con sus motores del laboratorio o una toolchain de destino.\n',
 }, ['include/main.inc'], description='NASM · src/, include/ con .inc, CMake y prueba de ejecución.'),
 'java': kit('Java', ['javac', 'java'], 'src/main/java/app/Main.java', {
    'src/main/java/app/Main.java': 'package app;\npublic final class Main {\n    public static int answer() { Answer service = new AnswerService(); return service.value(); }\n    public static void main(String[] args) { System.out.println(answer()); }\n}\n',
    'src/main/java/app/Answer.java': 'package app;\npublic interface Answer { int value(); }\n',
    'src/main/java/app/AnswerService.java': 'package app;\npublic final class AnswerService implements Answer {\n    @Override public int value() { return 42; }\n}\n',
    'src/test/java/app/MainTest.java': 'package app;\npublic final class MainTest {\n    public static void main(String[] args) { if (Main.answer() != 42) throw new AssertionError("answer"); }\n}\n',
    'src/main/resources/.gitkeep': '',
    'pom.xml': '<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>local.zenit</groupId><artifactId>zenit-project</artifactId><version>0.1.0</version><properties><maven.compiler.release>17</maven.compiler.release><maven.compiler.source>17</maven.compiler.source><maven.compiler.target>17</maven.compiler.target><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties></project>\n',
    'README.md': '# Proyecto Java\n\nsrc/main/java contiene clases y paquetes; src/test/java contiene las pruebas y src/main/resources los recursos.\nZénit usa javac/java del SDK seleccionado. Maven puede usar pom.xml cuando está instalado.\nPrueba sin dependencias: compila ambas clases con javac -d build/test-classes y ejecuta java -cp build/test-classes app.MainTest.\n',
 }, ['src/main/java/app/Answer.java'], ['src/main/java/app/Main.java','src/main/java/app/AnswerService.java'], description='Java · interfaz y clases en src/main/java, pruebas, recursos y pom.xml.'),
 'python': kit('Python', ['python'], 'src/zenit_app/main.py', {
    'src/zenit_app/__init__.py': '"""API pública del paquete."""\nfrom .main import answer\n\n__all__ = ["answer"]\n',
    'src/zenit_app/main.py': 'def answer():\n    return 42\n\ndef main():\n    print(answer())\n\nif __name__ == "__main__":\n    main()\n',
    'src/zenit_app/__main__.py': 'from .main import main\n\nmain()\n',
    'src/zenit_app/py.typed': '',
    'src/zenit_app/main.pyi': 'def answer() -> int: ...\ndef main() -> None: ...\n',
    'tests/test_main.py': 'import sys\nimport unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\nfrom zenit_app.main import answer\n\nclass MainTest(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 42)\n',
    'pyproject.toml': '[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "zenit-project"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n\n[project.scripts]\nzenit-app = "zenit_app.main:main"\n\n[tool.setuptools.packages.find]\nwhere = ["src"]\n\n[tool.setuptools.package-data]\nzenit_app = ["*.pyi", "py.typed"]\n',
    'README.md': '# Proyecto Python\n\nEl paquete está en src/zenit_app; las pruebas, en tests/. pyproject.toml describe el proyecto y py.typed marca sus tipos.\nEjecuta src/zenit_app/main.py o usa python -m unittest discover -s tests.\nCrea el entorno con python -m venv .venv o desde Dependencias de Python; Zénit lo detecta al ejecutar este proyecto.\nInstalar el paquete en modo editable (python -m pip install -e .) es una acción opcional.\n',
 }, ['src/zenit_app/__init__.py', 'src/zenit_app/main.pyi', 'src/zenit_app/py.typed'], description='Python · paquete y tipos .pyi en src/, pruebas, pyproject.toml y entorno .venv por proyecto.'),
 'rust': kit('Rust', ['rustc', 'cargo'], 'src/main.rs', {
    'Cargo.toml': '[package]\nname = "zenit_app"\nversion = "0.1.0"\nedition = "2021"\n',
    'src/main.rs': 'fn main() { println!("{}", zenit_app::answer()); }\n',
    'src/lib.rs': 'pub fn answer() -> i32 { 42 }\n',
    'tests/answer.rs': '#[test]\nfn answer_is_42() { assert_eq!(zenit_app::answer(), 42); }\n',
    'README.md': '# Proyecto Rust\n\nsrc/lib.rs expone la API del crate; src/main.rs es el programa y tests/ contiene las pruebas de integración.\nUsa cargo build, cargo run y cargo test. Zénit respeta Cargo.toml, genera Cargo.lock y conserva el caché de compilación del proyecto.\n',
 }, ['src/lib.rs'], description='Rust · Cargo.toml, crate en src/, biblioteca pública y pruebas de integración.'),
 'nc': {'label': 'nC', 'tools': ['ncc'], 'entry': None, 'files': {}, 'interfaces': [],
        'description': 'nC · paquete, módulos públicos y manifiesto creados por el compilador NCC real.'},
}
KITS['cpp']['files']['CMakeLists.txt'] = KITS['c']['files']['CMakeLists.txt'].replace(
    'LANGUAGES C)', 'LANGUAGES CXX)').replace('CMAKE_C_STANDARD 17', 'CMAKE_CXX_STANDARD 20').replace(
    'CMAKE_C_STANDARD_REQUIRED', 'CMAKE_CXX_STANDARD_REQUIRED').replace('.c)', '.cpp)')
for language, item in KITS.items():
    if item['entry']:
        descriptor=json.loads(item['files']['zenit.project.json']);descriptor['language']=language
        item['files']['zenit.project.json']=json.dumps(descriptor,indent=2)+'\n'
