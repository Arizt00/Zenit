"""Run with dist/Zenit/zenit-python.exe --python-child, never source Python."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from backend.server import Application
from backend.foundation import python_command
from backend.version import RELEASE_TAG
import backend.hilo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    report = parser.parse_args().report
    root = Path(sys._MEIPASS)
    assert Path(backend.hilo.__file__).is_relative_to(root)
    checks = ['Hilo and Lantern loaded from the frozen application']
    with tempfile.TemporaryDirectory(prefix='zenit-packaged-session-') as tmp:
        base = Path(tmp); workspace = base / 'project'; workspace.mkdir()
        (workspace / 'main.py').write_text('print("project preserved")\n')
        app = Application(root, workspace, data_dir=base / 'profile')
        app.workspace.trusted = True
        try:
            features = app.features; tern = features.tern; ws = app.workspace
            queued = features.post('/lantern/environments/create', {'kind': 'python', 'name': 'Packaged Python'})
            deadline = time.monotonic() + 120
            while True:
                job = next(j for j in features.hilo.snapshot()['jobs'] if j['id'] == queued['job'])
                if job['state'] not in ('queued', 'running'): break
                assert time.monotonic() < deadline, 'Environment preparation timed out'
                time.sleep(.1)
            assert job['state'] == 'done', job
            identity = job['result']['environment']; directory = tern.directory(ws, identity)
            checks.append('Hilo prepared a real environment using the bundled Python base')
            tern.activate(ws, identity)
            command = python_command(ws)
            assert Path(command[0]) == tern.python(directory)
            result = subprocess.run(command + ['-c', 'import sys, pip, debugpy; print(sys.prefix)'], capture_output=True, text=True, timeout=20)
            assert result.returncode == 0 and str(directory) in result.stdout, result.stderr
            checks.append('Execution uses the selected interpreter with bundled pip and debugpy')
            tern.save(ws, identity, 'packaged.tern'); tern.stop(ws, identity)
            assert directory.exists() and ws.environment_path == '.venv'
            tern.reopen(ws, 'packaged.tern'); tern.stop(ws, identity)
            checks.append('The saved environment survives closure and can be restored')
            connections = features.get('/hilo/connections', {})['connections']
            assert len(connections) == 7
            checks.append('All seven connection adapters are present in the frozen backend')
            assert 'project preserved' in (workspace / 'main.py').read_text()
        finally:
            app.features.shutdown(); app.runner.shutdown()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({'version': RELEASE_TAG, 'checks': checks, 'errors': []}, indent=2), encoding='utf-8')
    print(json.dumps({'checks': checks, 'errors': []}), flush=True)


if __name__ == '__main__': main()
