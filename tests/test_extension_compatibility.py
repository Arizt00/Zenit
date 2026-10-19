import unittest
from backend.extension_compatibility import evidence,matrix
class ExtensionCompatibilityTests(unittest.TestCase):
 def test_evidence_only_matches_reviewed_version_and_bytes(self):
  item=dict(matrix()['editorconfig.editorconfig']);self.assertTrue(evidence(item)['verified']);self.assertTrue(any('Monaco' in x for x in evidence(item)['tested']))
  for key,value in [('version','0.0.0'),('sha256','0'*64),('id','unknown.extension')]:self.assertFalse(evidence({**item,key:value})['verified'])
 def test_all_packaged_rows_identify_scope_and_exact_package(self):
  self.assertGreaterEqual(len(matrix()),16)
  for item in matrix().values():self.assertRegex(item['sha256'],'^[a-f0-9]{64}$');self.assertTrue(item['tested']);self.assertTrue(item['notVerified'])
if __name__=='__main__':unittest.main()
