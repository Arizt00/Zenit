"""Validate the actual Blender geometry consumed by the WebGL renderer."""
import hashlib
import json
import math
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CrystalAssetTests(unittest.TestCase):
    def test_double_wall_mesh_is_complete_and_matches_its_digest(self):
        info = json.loads((ROOT / 'web/assets/zenit-crystal.mesh.json').read_text())
        payload = (ROOT / 'web/assets/zenit-crystal.mesh.bin').read_bytes()
        self.assertEqual(len(payload), info['byteLength'])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), info['sha256'])
        self.assertTrue(info['generator'].startswith('Blender '))
        self.assertEqual(len(info['meshes']), 2)
        end = 0
        radii = []
        for mesh in info['meshes']:
            arrays = {}
            for name, kind in [('positions', 'f'), ('normals', 'f'), ('indices', 'I')]:
                record = mesh[name]
                self.assertEqual(record['byteOffset'], end)
                arrays[name] = struct.unpack_from('<' + str(record['count']) + kind, payload, end)
                end += record['count'] * 4
            self.assertEqual(len(arrays['positions']), mesh['vertices'] * 3)
            self.assertEqual(len(arrays['indices']), mesh['triangles'] * 3)
            self.assertLess(max(arrays['indices']), mesh['vertices'])
            for xyz in zip(*[iter(arrays['normals'])] * 3):
                self.assertAlmostEqual(sum(v*v for v in xyz), 1, places=5)
            radii.append(max(math.sqrt(sum(v*v for v in xyz)) for xyz in zip(*[iter(arrays['positions'])] * 3)))
        self.assertEqual(end, len(payload))
        self.assertGreater(radii[0], radii[1])
        self.assertAlmostEqual(radii[0], info['material']['outerRadius'], places=5)
        self.assertAlmostEqual(radii[1], info['material']['innerRadius'], places=5)
        self.assertTrue((ROOT / info['source']).is_file())


if __name__ == '__main__':
    unittest.main()
