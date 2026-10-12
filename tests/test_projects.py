import tempfile,unittest
from pathlib import Path
from backend.projects import create_project

class ProjectCreationTests(unittest.TestCase):
 def test_creates_real_empty_folder_with_unicode_without_overwriting(self):
  with tempfile.TemporaryDirectory() as tmp:
   result=create_project(tmp,'Proyecto ñ');folder=Path(result['path']);self.assertTrue(folder.is_dir());self.assertEqual(list(folder.iterdir()),[])
   (folder/'keep.py').write_text('keep')
   with self.assertRaises(FileExistsError):create_project(tmp,'Proyecto ñ')
   self.assertEqual((folder/'keep.py').read_text(),'keep')
 def test_rejects_traversal_and_windows_reserved_names(self):
  with tempfile.TemporaryDirectory() as tmp:
   for name in ['../outside','..','a/b','a\\b','NUL','COM1.py','invalid?', 'trailing.']:
    with self.subTest(name=name),self.assertRaises(ValueError):create_project(tmp,name)
if __name__=='__main__':unittest.main()
