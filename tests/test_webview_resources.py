"""Opaque webviews load scoped resources without receiving editor authority."""
import http.client
import json
from pathlib import Path
import re
import tempfile
import threading
from types import SimpleNamespace
import unittest
from urllib.parse import quote

from backend.server import Application, LumenServer

ROOT = Path(__file__).resolve().parents[1]


class WebviewResourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        workspace = base / 'project'; workspace.mkdir()
        self.extension = base / 'extension'; (self.extension / 'assets').mkdir(parents=True)
        self.script = self.extension / 'assets/app ñ.js'
        self.script.write_text('window.loaded = true;', encoding='utf-8')
        self.outside = base / 'private.txt'; self.outside.write_text('not an extension resource')
        self.app = Application(ROOT, workspace, data_dir=base / 'profile')
        self.app.workspace.trusted = True
        self.services = self.app.features.extension_services
        self.owner = SimpleNamespace(workspace=self.app.workspace, extension_id='qa.webview', extension_root=self.extension)
        self.services.call(self.owner, 'webview.create', {'id':'panel', 'options':{'enableScripts':True,'localResourceRoots':[str(self.extension)]}})
        self.server = LumenServer(0, self.app)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.app.features.shutdown(); self.app.runner.shutdown(); self.tmp.cleanup()

    def request(self, path):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def document(self):
        source='zenit-resource://panel/'+quote(str(self.script), safe='')
        html=f'<script src="{source}"></script>'
        result=self.services.webview_document('panel', html)
        token=result['url'].rsplit('/',1)[-1]
        rendered=self.services.webview_content(token)['html']
        return token,re.search(r'src="([^"]+)"',rendered)[1]

    def test_opaque_frame_resource_does_not_require_or_grant_editor_session(self):
        _, url=self.document()
        status,headers,raw=self.request(url)
        self.assertEqual(status,200);self.assertEqual(raw,self.script.read_bytes())
        self.assertEqual(headers['Access-Control-Allow-Origin'],'*')
        self.assertNotIn('Access-Control-Allow-Credentials',headers)
        self.assertIn('sandbox',headers['Content-Security-Policy'])
        self.assertEqual(self.request('/api/platform/settings')[0],403)

    def test_resource_capabilities_are_revoked_on_replacement_and_disposal(self):
        _, old=self.document();_,new=self.document()
        self.assertEqual(self.request(old)[0],404);self.assertEqual(self.request(new)[0],200)
        self.services.dispose_panel('panel')
        self.assertEqual(self.request(new)[0],404)

    def test_resource_roots_reject_traversal_other_panels_and_unknown_capabilities(self):
        token,_=self.document()
        for suffix in ('0/../private.txt','0/%2e%2e/private.txt','99/private.txt','0/C%3A/private.txt'):
            self.assertNotEqual(self.request('/extension-webview-resource/'+token+'/'+suffix)[0],200)
        self.assertEqual(self.request('/extension-webview-resource/unknown/0/assets/app.js')[0],404)
        for source in ('zenit-resource://other/'+quote(str(self.script),safe=''),'zenit-resource://panel/'+quote(str(self.outside),safe='')):
            with self.assertRaises(PermissionError):self.services.webview_document('panel','<script src="'+source+'"></script>')

    def test_initial_state_is_data_and_csp_retains_extension_nonce(self):
        result=self.services.webview_document('panel','<meta http-equiv="Content-Security-Policy" content="img-src vscode-resource:; script-src \'nonce-qa\'"><script nonce="qa" data-initial-state>{"value":42}</script>')
        document=self.services.webview_content(result['url'].rsplit('/',1)[-1])['html']
        self.assertIn('zenit-webview-source:',document)
        self.assertIn("script-src 'nonce-qa'",document)
        self.assertIn('<script type="application/json" nonce="qa" data-initial-state>',document)


if __name__ == '__main__': unittest.main()
