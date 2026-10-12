"""Protect canonical references from accidental regeneration by the capture runner."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GoldenReferenceTests(unittest.TestCase):
    def test_later_minimal_welcome_reference_is_preserved(self):
        folder = ROOT / 'tests/visual'
        brief = json.loads((folder / 'welcome-brief.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((folder / brief['reference']).read_bytes()).hexdigest(), brief['sha256'])

    def test_active_design_contains_no_mojibake(self):
        for path in (ROOT / 'web/design').glob('*.css'):
            with self.subTest(stylesheet=path.name):
                text = path.read_text(encoding='utf-8')
                self.assertNotRegex(text, '[\u00c3\u00c2\ufffd]')

    def test_original_reference_bytes_are_immutable(self):
        folder = ROOT / 'tests/visual'
        manifest = json.loads((folder / 'goldens.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['references']), 8)
        for item in manifest['references']:
            with self.subTest(view=item['view']):
                actual = hashlib.sha256((folder / item['file']).read_bytes()).hexdigest()
                self.assertEqual(actual, item['sha256'])

    def test_capture_does_not_replace_golden_masters(self):
        from tools.visual_compare import compare
        from PIL import Image
        import tempfile
        with tempfile.TemporaryDirectory(prefix='zenit-diff-test-') as directory:
            path = Path(directory)
            a = path / 'reference.png'
            b = path / 'actual.png'
            Image.new('RGB', (64, 40), 'white').save(a)
            Image.new('RGB', (60, 40), 'white').save(b)
            original = a.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Viewport mismatch'):
                compare(a, b, path / 'comparison')
            self.assertEqual(a.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
