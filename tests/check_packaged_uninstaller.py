"""Exercise the shipped EXE and its native bridge against disposable data only.

Usage: python tests/check_packaged_uninstaller.py --exe dist/Uninstall-Zenit.exe --output qa-output/uninstall
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    executable = args.exe.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='zenit-uninstall-native-test-') as temporary:
        base = Path(temporary).resolve()
        root = base / 'Installed Zenit'
        version = root / 'app-0.5.4-R11'
        sdk_file = version / 'sdk/foundation/native-mingw/lib/tcl8.6/msgs/af.msg'
        sdk_file.parent.mkdir(parents=True)
        sdk_file.write_bytes(b'read-only SDK message fixture')
        sdk_file.chmod(stat.S_IREAD)
        (root / 'installation.json').write_text(json.dumps({'version': '0.5.4', 'directory': version.name}))
        installed = root / 'Uninstall-Zenit.exe'
        shutil.copy2(executable, installed)
        profile = base / 'profile'
        project = profile / 'workspaces/MyProject/main.py'
        project.parent.mkdir(parents=True)
        project.write_bytes(b'print("keep this project")\n')
        preferences = profile / 'preferences.json'
        preferences.write_bytes(b'{"keep":"settings and memories"}')
        external = base / 'external-project.txt'
        external.write_bytes(b'keep external project')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        env = dict(os.environ, ZENIT_DATA_DIR=str(profile), WEBVIEW2_USER_DATA_FOLDER=str(base / 'webview-test'),
                   WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-port={port} --remote-debugging-address=127.0.0.1')
        process = subprocess.Popen([str(installed), '--target', str(root)], env=env, cwd=root,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        endpoint = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + 45
        while True:
            try:
                with urlopen(endpoint + '/json/version', timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise RuntimeError('The native uninstaller did not expose its test browser in time.')
                time.sleep(.2)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.wait_for_event('page')
            page.on('pageerror', lambda error: errors.append(str(error)))
            try:
                expect(page.locator('#review')).to_be_visible(timeout=20000)
                info = page.evaluate('() => window.pywebview.api.info()')
                assert Path(info['installation']).resolve() == root
                assert Path(info['dataDirectory']).resolve() == profile
                assert not page.locator('#data').is_checked()
                page.screenshot(path=str(output / 'uninstall-review-options.png'))
                page.locator('#review').click()
                expect(page.locator('#content')).to_contain_text('All your projects will be kept.')
                page.locator('#remove').click()
                expect(page.locator('#content')).to_contain_text('Zénit was uninstalled successfully.', timeout=30000)
                state = page.evaluate('() => window.pywebview.api.status()')
                assert state['status'] == 'finished', state
                assert not root.exists(), 'The copied uninstaller must relocate and remove its own installation.'
                assert project.read_bytes() == b'print("keep this project")\n'
                assert preferences.read_bytes() == b'{"keep":"settings and memories"}'
                assert external.read_bytes() == b'keep external project'
                assert not errors, errors
                page.screenshot(path=str(output / 'uninstall-success.png'))
                evidence = {'status': 'passed', 'executable': executable.name,
                            'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                            'checks': ['Real packaged native UI and bridge', 'Self relocation before removal',
                                       'Read-only toolchain file removed', 'Default data deletion disabled',
                                       'Profile and internal/external projects preserved', 'No JavaScript errors']}
                (output / 'packaged-uninstaller.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
                print(json.dumps(evidence), flush=True)
            finally:
                if not page.is_closed():
                    page.locator('#close, #cancel').first.click(timeout=3000, no_wait_after=True)
        process.wait(timeout=15)
        # WebView2 releases its own temporary profile asynchronously after close.
        time.sleep(2)


if __name__ == '__main__':
    main()
