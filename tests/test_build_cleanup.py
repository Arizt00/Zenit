import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from tools.build_desktop import prepare_windows_bundle_cleanup


@unittest.skipUnless(os.name == 'nt', 'Windows SDK file attributes')
class BuildCleanupTests(unittest.TestCase):
    def test_readonly_sdk_can_be_replaced_and_other_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'dist/Zenit'
            bundle.mkdir(parents=True)
            sdk = bundle / 'af.msg'
            sdk.write_bytes(b'SDK message')
            sdk.chmod(stat.S_IREAD)
            outside = root / 'project.py'
            outside.write_text('keep')
            with patch('tools.build_desktop.ROOT', root):
                with self.assertRaises(ValueError): prepare_windows_bundle_cleanup(root)
                prepare_windows_bundle_cleanup(bundle)
            self.assertFalse(sdk.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
            sdk.unlink()
            self.assertEqual(outside.read_text(), 'keep')


if __name__ == '__main__': unittest.main()
