import tempfile,unittest
from pathlib import Path
from backend.extension_command_icons import command_icons
class CommandIconTest(unittest.TestCase):
 def test_themed_images_and_declared_symbols_are_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'action.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M1 1h2"/></svg>')
   icons=command_icons(root,{'contributes':{'commands':[{'command':'qa.run','icon':'$(play)'},{'command':'qa.theme','icon':{'light':'action.svg','dark':'action.svg'}}]}})
   self.assertEqual(icons['qa.run'],'$(play)');self.assertTrue(icons['qa.theme']['dark'].startswith('data:image/svg+xml;base64,'))
 def test_external_active_and_oversized_resources_are_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'extension';root.mkdir();(Path(tmp)/'outside.svg').write_text('<svg/>');(root/'active.svg').write_text('<svg><script>alert(1)</script></svg>');(root/'big.svg').write_text('<svg>'+(' '*33000)+'</svg>')
   data={'contributes':{'commands':[{'command':path,'icon':path} for path in ('../outside.svg','active.svg','big.svg','https://example.test/icon.svg')]}}
   self.assertEqual(command_icons(root,data),{})
if __name__=='__main__':unittest.main()
