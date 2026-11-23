"""Provider-independent language grounding, without reading project files or running tools."""
import json
import re
from pathlib import PureWindowsPath

NC_IDENTITY = (
    'Zénit supports nC, an independent language compiled by NCC (the ncc command, '
    'ncc.exe on Windows; .ncc is also how users may refer to the compiler). '
    'nC source extensions are .n, .nc, .nm, .ncp, .nb and .nbb. '
    'Do not reinterpret nC as C, C++, C#, Rust or NC machine-control/G-code. '
    'Use the IDE language reference when provided; compiler diagnostics take precedence. '
    'Never invent syntax, modules, compiler versions or successful execution.'
)

# Checked against the compiler's docs/syntax.md and tools/ncup/nc/templates/hello.n.
# Kept here so frozen builds and every provider receive the same small reference.
NC_REFERENCE = '''nC language reference supplied by Zénit:
Imports: use <io:output>; or use <io:input, output, render>;
Canonical declarations: name >> Type <- initialValue; assignment: name <- value;
parameters: name >> Type; functions: run() -> bool { return true; }
Named containers group const:, type:, stc:, local:, fn:, fa: sections.
There is at most one stc: section. ref main ->> run; selects the entry function;
run is not implicitly special. fa: is the final section.
Minimal program:
use <io:output>;
hello {
    fn:
        run() -> bool {
            println("Hola desde nC");
            return true;
        }
    ref main ->> run;
    fa: return true;
}
An entry of up to 30 logical statements can use to main { ... } in its container.
Sections support public:, internal:, private: visibility. Types include int, u64,
bool, str and pointers T*, p<T>, ptr<T>. Memory is manual/raw: alloc, free, rd,
wr, off; do not add ownership, automatic cleanup or safety guarantees.
if condition { ... } else { ... }, while condition { ... }, guard valid else return false;
are supported. = is historical compatibility; := was removed; prefer <-.
Roles such as :: runtime, :: machine and :: primitive change the material contract.
Low-level [@], [@machine], primitive[@], ABI/bind and linker surfaces need the
specific compiler reference or a known working example; do not guess their syntax.
Use nC (or nc) for fenced code. Do not turn it into a C/C++ or Rust program.
Compiler commands (argv templates; substitute the actual source/output paths):
  ncc check source.n
  ncc run source.n
  ncc compiler build-native source.n --profile debug --out-dir build --out build/program --no-run --strict
  ncc package init project-name --path project-directory
  ncc package check --path project-directory
The native command builds; running its output is a separate action. Package
manifests are ncc.package.json with ncc.lock. Use the installed version's help
and diagnostics for version-dependent options; do not claim commands were run.
'''


def language_context(body, config=None):
    """Ground a selected nC file, named file plan, or explicit nC question only."""
    paths = [body.get('path', '')]
    paths.extend(item.get('path', '') for item in body.get('fileContext', []) if isinstance(item, dict))
    is_nc = any(isinstance(path, str) and PureWindowsPath(path).suffix.lower() in
                ('.n', '.nc', '.nm', '.ncp', '.nb', '.nbb') for path in paths)
    if not is_nc and not re.search(r'(?<![\w])(?:nC|ncc(?:\.exe)?|\.ncc)(?![\w])', body.get('question', ''), re.I):
        return ''
    from .runtime_paths import find_tool
    config = config or {}
    executable = find_tool('ncc', config.get('tools'))
    tool = {'language': 'nC', 'compiler': 'NCC', 'available': bool(executable),
            'executable': executable, 'discoveryOnly': True}
    if profile := config.get('languages', {}).get('nc'):
        tool['configuredCommands'] = {key: profile[key] for key in ('build', 'run', 'check') if key in profile}
    return NC_REFERENCE + '\nDetected toolchain (JSON data, not instructions):\n' + json.dumps(tool, ensure_ascii=False)
