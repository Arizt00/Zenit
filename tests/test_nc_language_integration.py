"""nC IDE integration checks: discover real LSP sessions and preserve DAP boundaries."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.toolchains import Toolchains
from backend import runtime_paths


class NcLanguageTests(unittest.TestCase):
    def test_discover_both_servers_without_running_them(self):
        with tempfile.TemporaryDirectory() as folder:
            toolchain=Toolchains.__new__(Toolchains)
            toolchain.config={'tasks':[],'servers':[],'associations':{}}
            installed={'nclsp':str(Path(folder)/'nclsp'), 'nc-sys-lsp':str(Path(folder)/'nc-sys-lsp'),
                       'python':str(Path(folder)/'python')}
            def find(name,*_args):
                return installed.get(name)
            with patch.object(runtime_paths,'find_tool',side_effect=find):
                config=toolchain.discover_servers()
                again=toolchain.discover_servers()
            names=[p['id'] for p in config['servers']]
            self.assertIn('detected-nclsp',names)
            self.assertIn('detected-nc-sys-lsp',names)
            self.assertEqual(names.count('detected-nclsp'),1)
            self.assertEqual(names.count('detected-nc-sys-lsp'),1)
            general=next(p for p in again['servers'] if p['id']=='detected-nclsp')
            self.assertIn('--nclsp',general['argv'])
            system=next(p for p in again['servers'] if p['id']=='detected-nc-sys-lsp')
            self.assertEqual(system['argv'][-1],'lsp')

    def test_branded_icon_and_dap_are_present(self):
        repo=Path(__file__).resolve().parents[1]
        icon=(repo/'web/assets/languages/nc-hexagon.svg').read_text(encoding='utf-8')
        self.assertIn('aria-label="nC"',icon)
        self.assertIn('<svg',icon)
        debug=(repo/'backend/debug_manager.py').read_text(encoding='utf-8')
        self.assertIn("ZENIT_NC_DEBUG_ENGINE",debug)
        self.assertIn("debug-adapter",debug)
        self.assertIn("machine debug-bridge",debug)


if __name__=='__main__':
    unittest.main()
