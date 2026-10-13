import json
import tempfile
import unittest
from pathlib import Path
from launcher import resolve_launch


class Launcher(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for name in ['app-0.5.3-R13','app-0.5.4-R2','app-0.5.4-R2-previous-999']:
            (self.root/name).mkdir();(self.root/name/'zenit.exe').write_bytes(b'QA executable')
    def tearDown(self):self.temp.cleanup()
    def test_manifest_is_the_active_installation(self):
        (self.root/'installation.json').write_text(json.dumps({'directory':'app-0.5.3-R13'}))
        self.assertEqual(resolve_launch(self.root).parent.name,'app-0.5.3-R13')
    def test_missing_or_corrupt_manifest_recovers_the_newest_complete_payload(self):
        self.assertEqual(resolve_launch(self.root).parent.name,'app-0.5.4-R2')
        (self.root/'installation.json').write_text('{bad')
        self.assertEqual(resolve_launch(self.root).parent.name,'app-0.5.4-R2')
    def test_manifest_cannot_escape_and_backups_are_not_launchable(self):
        (self.root/'installation.json').write_text(json.dumps({'directory':'../elsewhere'}))
        self.assertEqual(resolve_launch(self.root).parent.name,'app-0.5.4-R2')
        (self.root/'app-0.5.4-R2'/'zenit.exe').unlink();(self.root/'app-0.5.3-R13'/'zenit.exe').unlink()
        with self.assertRaises(FileNotFoundError):resolve_launch(self.root)


if __name__=='__main__':unittest.main()
