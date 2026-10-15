"""Regression coverage for read-only SDK files and recoverable Windows uninstall."""
import ctypes
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.uninstall import Uninstaller, retry_readonly
from backend import windows_installation
from backend.version import VERSION
from installer import Installer


@contextmanager
def locked_file(path):
    """A real Windows handle that permits reads but prevents deletion."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


@unittest.skipUnless(os.name == 'nt', 'Windows file attributes and sharing modes')
class UninstallRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zenit-uninstall-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'Installed Zenit'
        self.version = self.root / 'app-0.5.4-R11'
        self.version.mkdir(parents=True)
        self.file = self.version / 'sdk/foundation/native-mingw/lib/tcl8.6/msgs/af.msg'
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b'bundled SDK fixture')
        self.manifest = self.root / 'installation.json'
        self.manifest.write_text(json.dumps({'directories': ['app-0.5.4-R10', self.version.name]}))
        for name in ('Zenit.exe', 'Uninstall-Zenit.exe'):
            (self.root / name).write_bytes(b'owned launcher fixture')
        self.profile = self.base / 'profile'
        (self.profile / 'workspaces/Project').mkdir(parents=True)
        (self.profile / 'workspaces/Project/main.py').write_bytes(b'precious source')
        (self.profile / 'preferences.json').write_bytes(b'{"keep":true}')
        self.outside = self.base / 'external-project.bin'
        self.outside.write_bytes(bytes(range(256)))

    def remove(self, **options):
        service = Uninstaller(self.root, self.profile, integrate_windows=False)
        service.start({'confirm': True, **options})
        deadline = time.monotonic() + 10
        while service.status()['status'] == 'removing' and time.monotonic() < deadline:
            time.sleep(.01)
        return service.status()

    def assert_kept_data(self):
        self.assertEqual((self.profile / 'preferences.json').read_bytes(), b'{"keep":true}')
        self.assertEqual((self.profile / 'workspaces/Project/main.py').read_bytes(), b'precious source')
        self.assertEqual(self.outside.read_bytes(), bytes(range(256)))

    def test_readonly_sdk_and_owned_launchers_uninstall_without_changing_user_files(self):
        for path in (self.file, self.root / 'Zenit.exe', self.manifest, self.outside):
            path.chmod(stat.S_IREAD)
            self.assertTrue(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
        # Shared SDKs and files not declared by the installation remain intact.
        shared = self.root / 'sdk/shared.txt'
        shared.parent.mkdir()
        shared.write_text('shared SDK')
        result = self.remove()
        self.assertEqual(result['status'], 'finished', result)
        self.assertFalse(self.version.exists())
        self.assertFalse(self.manifest.exists())
        self.assertEqual(shared.read_text(), 'shared SDK')
        self.assert_kept_data()
        self.assertTrue(self.outside.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)

    def test_locked_sdk_reports_error_and_a_new_session_can_resume(self):
        self.file.chmod(stat.S_IREAD)
        with locked_file(self.file):
            result = self.remove()
            self.assertEqual(result['status'], 'error', result)
            self.assertIn('af.msg', result['message'])
            self.assertTrue(self.manifest.is_file())
            self.assertTrue((self.root / 'Uninstall-Zenit.exe').is_file())
            self.assert_kept_data()
        result = self.remove()
        self.assertEqual(result['status'], 'finished', result)
        self.assertFalse(self.root.exists())
        self.assert_kept_data()

    def test_locked_root_launcher_keeps_manifest_for_retry_after_version_removal(self):
        with locked_file(self.root / 'Zenit.exe'):
            result = self.remove()
            self.assertEqual(result['status'], 'error', result)
            self.assertFalse(self.version.exists())
            self.assertTrue(self.manifest.is_file())
            self.assertTrue((self.root / 'Uninstall-Zenit.exe').is_file())
        result = self.remove()
        self.assertEqual(result['status'], 'finished', result)
        self.assert_kept_data()

    def test_readonly_recovery_rejects_files_outside_the_removal_root(self):
        self.outside.chmod(stat.S_IREAD)
        error = PermissionError('read only')
        with self.assertRaises(ValueError):
            retry_readonly(os.unlink, self.outside, (PermissionError, error, None), root=self.version)
        self.assertTrue(self.outside.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
        self.assert_kept_data()

    def test_junction_to_external_project_is_never_traversed(self):
        junction = self.version / 'linked-profile'
        command = "New-Item -ItemType Junction -Path '{}' -Target '{}' | Out-Null".format(
            str(junction).replace("'", "''"), str(self.profile).replace("'", "''"))
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                       check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            result = self.remove()
            self.assertEqual(result['status'], 'error', result)
            self.assertTrue(self.manifest.is_file())
            self.assert_kept_data()
        finally:
            # Removing the junction itself does not recursively touch its target.
            junction.rmdir()

    def test_explicit_settings_removal_accepts_readonly_files_and_preserves_projects(self):
        (self.profile / 'preferences.json').chmod(stat.S_IREAD)
        result = self.remove(deleteData=True)
        self.assertEqual(result['status'], 'finished', result)
        self.assertFalse((self.profile / 'preferences.json').exists())
        self.assertEqual((self.profile / 'workspaces/Project/main.py').read_bytes(), b'precious source')


@unittest.skipUnless(os.name == 'nt', 'Windows Installed apps registration')
class WindowsRegistrationTests(unittest.TestCase):
    def setUp(self):
        import winreg
        self.winreg = winreg
        self.temp = tempfile.TemporaryDirectory(prefix='zenit-registration-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'Installed Zénit IDE'
        self.root.mkdir()
        self.runtime = self.base / 'bundle'
        self.runtime.mkdir()
        (self.runtime / 'Uninstall-Zenit.exe').write_bytes(b'corrected uninstaller')
        (self.root / 'Zenit.exe').write_bytes(b'stable launcher')
        # Exercise real HKCU writes without touching any Installed apps entry.
        self.key = r'Software\ZenitUninstallTest-' + uuid4().hex
        self.addCleanup(self.delete_key)
        replacement = patch.object(windows_installation, 'UNINSTALL_KEY', self.key)
        replacement.start()
        self.addCleanup(replacement.stop)

    def delete_key(self):
        try:
            self.winreg.DeleteKey(self.winreg.HKEY_CURRENT_USER, self.key)
        except FileNotFoundError:
            pass

    def test_installer_repairs_hidden_entry_and_uses_stable_paths_with_explicit_target(self):
        reg = self.winreg
        with reg.CreateKey(reg.HKEY_CURRENT_USER, self.key) as entry:
            reg.SetValueEx(entry, 'SystemComponent', 0, reg.REG_DWORD, 1)
            reg.SetValueEx(entry, 'NoRemove', 0, reg.REG_DWORD, 1)
            reg.SetValueEx(entry, 'InstallLocation', 0, reg.REG_SZ, str(self.root / 'app-removed'))
        with patch('installer.ROOT', self.runtime):
            Installer(target=self.root)._register(self.root / 'app-removed')
        with reg.OpenKey(reg.HKEY_CURRENT_USER, self.key) as entry:
            value = lambda name: reg.QueryValueEx(entry, name)
            self.assertEqual(value('DisplayName'), ('Zénit IDE', reg.REG_SZ))
            self.assertEqual(value('DisplayVersion')[0], VERSION)
            self.assertEqual(value('InstallLocation')[0], str(self.root.resolve()))
            self.assertEqual(value('DisplayIcon')[0], f'"{self.root / "Zenit.exe"}",0')
            self.assertEqual(value('SystemComponent'), (0, reg.REG_DWORD))
            self.assertEqual(value('NoRemove'), (0, reg.REG_DWORD))
            self.assertEqual(value('NoModify'), (1, reg.REG_DWORD))
            self.assertEqual(value('NoRepair'), (1, reg.REG_DWORD))
            command = value('UninstallString')[0]
        shell = ctypes.WinDLL('shell32')
        shell.CommandLineToArgvW.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int))
        shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        count = ctypes.c_int()
        parsed = shell.CommandLineToArgvW(command, ctypes.byref(count))
        try:
            self.assertEqual(list(parsed[:count.value]), [str(self.root / 'Uninstall-Zenit.exe'), '--target', str(self.root)])
        finally:
            kernel = ctypes.WinDLL('kernel32')
            kernel.LocalFree.argtypes = (ctypes.c_void_p,)
            kernel.LocalFree(parsed)
        self.assertEqual((self.root / 'Uninstall-Zenit.exe').read_bytes(), b'corrected uninstaller')

    def test_missing_uninstaller_never_registers_a_broken_command(self):
        with self.assertRaises(FileNotFoundError):
            windows_installation.register_uninstaller(self.root, VERSION)
        with self.assertRaises(FileNotFoundError):
            self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, self.key)


if __name__ == '__main__':
    unittest.main()
