import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend.startup import appearance


class StartupAppearance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.settings={'appearance.theme':'forest','appearance.extensionTheme':''}
        self.extensions=SimpleNamespace(root=self.root,installed={})

    def tearDown(self):
        self.temp.cleanup()

    def theme(self,ui='vs-dark'):
        folder=self.root/'theme-package'/'extension';folder.mkdir(parents=True)
        (folder/'package.json').write_text(json.dumps({'contributes':{'themes':[{'id':'night','label':'Night','uiTheme':ui}]}}),encoding='utf-8')
        self.extensions.installed['qa.theme']={'directory':'theme-package','enabled':True}
        self.settings['appearance.extensionTheme']='qa.theme:night'

    def test_native_profile_theme_without_browser_storage(self):
        self.assertEqual(appearance(self.settings,self.extensions),{'base':'forest','extension':''})

    def test_actual_extension_declaration_controls_the_first_paint(self):
        self.theme()
        self.assertEqual(appearance(self.settings,self.extensions),{'base':'dark','extension':'qa.theme:night'})

    def test_light_and_disabled_themes(self):
        self.theme('vs')
        self.assertEqual(appearance(self.settings,self.extensions)['base'],'day')
        self.extensions.installed['qa.theme']['enabled']=False
        self.assertEqual(appearance(self.settings,self.extensions),{'base':'forest','extension':''})

    def test_stale_identity_and_unsafe_package_never_seed_the_cache(self):
        self.theme()
        self.settings['appearance.extensionTheme']='qa.theme:missing'
        self.assertEqual(appearance(self.settings,self.extensions)['extension'],'')
        self.settings['appearance.extensionTheme']='qa.theme:night'
        self.extensions.installed['qa.theme']['directory']='../outside'
        self.assertEqual(appearance(self.settings,self.extensions)['extension'],'')


if __name__=='__main__':unittest.main()
