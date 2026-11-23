import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.extension_accounts import ExtensionAccounts
from backend.preferences import Preferences

class Response:
    headers={'X-OAuth-Scopes':'user, repo, workflow'}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return b'{"id":42,"login":"fixture-account"}'

class ExtensionAccountTests(unittest.TestCase):
    def test_real_response_scopes_session_only_no_token_in_status_or_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            changes=[];a=ExtensionAccounts(Preferences(Path(tmp)),lambda:changes.append(True))
            self.assertFalse(a.snapshot()['github']['connected']);self.assertEqual(a.sessions([]),[])
            with patch('backend.extension_accounts.CredentialVault._native',return_value=None),patch('urllib.request.OpenerDirector.open',return_value=Response()) as opened:
                a.connect({'token':'test-fixture-credential','consent':True})
            self.assertEqual(opened.call_args.args[0].full_url,'https://api.github.com/user')
            self.assertNotIn('test-fixture-credential',json.dumps(a.snapshot())+a.path.read_text())
            self.assertEqual(a.sessions(['read:user','repo','workflow'])[0]['account']['label'],'fixture-account')
            self.assertEqual(a.sessions(['admin:org']),[])
            self.assertFalse(ExtensionAccounts(Preferences(Path(tmp))).snapshot()['github']['connected'])
            with self.assertRaisesRegex(ValueError,'Conecta'):a.sessions(['admin:org'],create=True)
            with patch('backend.extension_accounts.CredentialVault._native',return_value=None):a.disconnect()
            self.assertEqual(a.sessions([]),[]);self.assertEqual(len(changes),2)

    def test_no_silent_connection_or_fabricated_fine_grained_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=ExtensionAccounts(Preferences(Path(tmp)))
            with self.assertRaises(PermissionError):a.connect({'token':'test-fixture'})
            response=Response();response.headers={}
            with patch('backend.extension_accounts.CredentialVault._native',return_value=None),patch('urllib.request.OpenerDirector.open',return_value=response):a.connect({'token':'test-fixture','consent':True})
            self.assertEqual(a.sessions(['repo']),[]);self.assertEqual(len(a.sessions([])),1)
            with patch('backend.extension_accounts.CredentialVault._native',return_value=None),self.assertRaisesRegex(ValueError,'seguro'):a.connect({'token':'test-fixture','remember':True,'consent':True})

if __name__=='__main__':unittest.main()
