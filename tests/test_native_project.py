"""Real builds, preserved project files and a usable generated CMake project."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch
from backend.server import Application
from backend.foundation import bundled_tool, tool_environment
from backend.runtime_paths import find_tool

ROOT = Path(__file__).resolve().parents[1]


class NativeProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zenit-project-', ignore_cleanup_errors=True)
        self.base = Path(self.tmp.name)
        self.ws = self.base / 'Project with spaces'
        self.ws.mkdir()
        self.app = Application(ROOT, self.ws, data_dir=self.base / 'profile')
        self.app.workspace.trusted = True
        self.rt = self.app.features.runtimes

    def tearDown(self):
        self.app.features.shutdown()
        self.app.runner.shutdown()
        self.tmp.cleanup()

    def execute(self, commands):
        job = self.app.runner.jobs[self.app.runner.start(commands, self.ws, timeout=60, env=tool_environment())['job']]
        deadline = time.monotonic() + 70
        while not job.done and time.monotonic() < deadline:
            time.sleep(.03)
        self.assertTrue(job.done, job.output)
        self.assertEqual(job.code, 0, job.output)
        return job.output

    def test_c_and_cpp_generate_build_header_intermediates_and_execute(self):
        for name, code, text in [('sum.c', '#include <stdio.h>\nint main(void){puts("REAL_C");return 0;}\n', 'REAL_C'),
                                 ('sum.cpp', '#include <iostream>\nint main(){std::cout << "REAL_CPP";return 0;}\n', 'REAL_CPP')]:
            (self.ws / name).write_text(code)
            plan = self.rt.plan(self.app.workspace, name)
            self.assertIn(text, self.execute(plan['commands']))
            artifacts = plan['artifacts']
            self.assertTrue((self.ws / artifacts['header']).is_file())
            self.assertTrue((self.ws / 'CMakeLists.txt').is_file())
            self.assertTrue(plan['target'].is_file())
            self.assertTrue(list(plan['target'].parent.glob('*.o')))
            self.assertTrue(list(plan['target'].parent.glob('*.s')))
            self.assertTrue(list(plan['target'].parent.glob('*.i*')))
            self.assertEqual((self.ws / name).read_text(), code)

    @unittest.skipUnless(bundled_tool('cmake') and bundled_tool('ninja'), 'Prepared CMake and Ninja required')
    def test_generated_cmake_rebuilds_real_binary_and_is_incremental(self):
        path = self.ws / 'has spaces.c'
        path.write_text('#include <stdio.h>\nint main(void){puts("CMAKE_ONE");return 0;}\n')
        plan = self.rt.plan(self.app.workspace, path.name)
        build = self.base / 'cmake build'
        cmake = bundled_tool('cmake')
        self.execute([[cmake, '-S', str(self.ws), '-B', str(build), '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + bundled_tool('ninja')],
                      [cmake, '--build', str(build)]])
        self.assertIn('CMAKE_ONE', self.execute([[str(plan['target'])]]))
        timestamp = plan['target'].stat().st_mtime_ns
        self.execute([[cmake, '--build', str(build)]])
        self.assertEqual(plan['target'].stat().st_mtime_ns, timestamp)
        path.write_text('#include <stdio.h>\nint main(void){puts("CMAKE_TWO");return 0;}\n')
        self.execute([[cmake, '--build', str(build)]])
        self.assertIn('CMAKE_TWO', self.execute([[str(plan['target'])]]))

    def test_existing_header_build_files_and_sources_are_preserved(self):
        for name, content in {'CMakeLists.txt': '# custom project\n', 'main.h': '// user interface\n',
                              'main.c': 'int main(void){return 0;}\n', 'Cargo.toml': '# custom cargo\n',
                              'ncc.package.json': '{"schema":"ncc.package.v1","dependencies":[]}'}.items():
            (self.ws / name).write_text(content)
        original = {p: p.read_bytes() for p in self.ws.iterdir() if p.is_file()}
        plan = self.rt.plan(self.app.workspace, 'main.c')
        self.execute(plan['commands'])
        self.assertEqual(plan['artifacts']['created'], [])
        self.assertTrue((self.ws / plan['artifacts']['cmake']).is_file())
        for path, raw in original.items(): self.assertEqual(path.read_bytes(), raw)

    def test_checks_untrusted_and_missing_compilers_never_scaffold(self):
        (self.ws / 'main.c').write_text('int main(void){return 0;}\n')
        self.execute(self.rt.plan(self.app.workspace, 'main.c', check=True)['commands'])
        self.assertFalse((self.ws / 'CMakeLists.txt').exists())
        self.assertFalse((self.ws / 'main.h').exists())
        self.app.workspace.trusted = False
        with self.assertRaises(PermissionError): self.rt.plan(self.app.workspace, 'main.c')
        self.app.workspace.trusted = True
        (self.ws / 'main.rs').write_text('fn main() {}')
        with patch('backend.runtimes.find_tool', return_value=None):
            with self.assertRaisesRegex(ValueError, 'rustc'): self.rt.plan(self.app.workspace, 'main.rs')
        self.assertFalse((self.ws / 'Cargo.toml').exists())

    @unittest.skipUnless(bundled_tool('ncc'), 'Prepared nC compiler required')
    def test_nc_compiles_once_to_a_real_native_executable_and_manifest(self):
        path = self.ws / 'main.n'
        path.write_text('use <io:output, render>;\napp :: runtime {\n fn:\n run() -> int { println("REAL_NC"); return 0; }\n ref main ->> run;\n fa:\n return true;\n}\n')
        plan = self.rt.plan(self.app.workspace, path.name)
        self.assertEqual(len(plan['commands']), 2)
        self.assertEqual(plan['commands'][0][1:3], ['compiler', 'build-native'])
        self.assertIn('REAL_NC', self.execute(plan['commands']))
        self.assertTrue(plan['target'].is_file())
        manifest = json.loads((self.ws / 'ncc.package.json').read_text())
        self.assertEqual(manifest['targets']['main'], 'main.n')
        self.assertTrue((self.ws / 'main.h').is_file())
        before = (self.ws / 'ncc.package.json').read_bytes()
        self.assertIn('REAL_NC', self.execute(self.rt.plan(self.app.workspace, path.name)['commands']))
        self.assertEqual((self.ws / 'ncc.package.json').read_bytes(), before)

    def test_rust_manifest_is_valid_and_existing_cargo_is_never_replaced(self):
        (self.ws / 'sample.rs').write_text('fn main() { println!("RUST_OK"); }')
        with patch('backend.runtimes.find_tool', return_value='rustc'):
            plan = self.rt.plan(self.app.workspace, 'sample.rs')
        manifest = tomllib.loads((self.ws / 'Cargo.toml').read_text())
        self.assertEqual(manifest['bin'][0]['path'], 'sample.rs')
        self.assertEqual(plan['artifacts']['headerKind'], 'optional-c-abi')
        (self.ws / 'Cargo.toml').write_text('# Customized by the programmer\n')
        with patch('backend.runtimes.find_tool', return_value='rustc'):
            self.rt.plan(self.app.workspace, 'sample.rs')
        self.assertEqual((self.ws / 'Cargo.toml').read_text(), '# Customized by the programmer\n')

    @unittest.skipUnless(find_tool('rustc'), 'Rust is not installed on this station')
    def test_installed_rust_compiles_and_runs(self):
        (self.ws / 'main.rs').write_text('fn main() { println!("RUST_OK"); }')
        plan = self.rt.plan(self.app.workspace, 'main.rs')
        self.assertIn('RUST_OK', self.execute(plan['commands']))


if __name__ == '__main__':
    unittest.main()
