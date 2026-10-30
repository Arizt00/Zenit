"""Real resumable HTTP download/hash lifecycle, with a tiny local GGUF fixture."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from backend.ai_models import AIModels, MODEL_CATALOG
from backend.downloads import Downloads


class ModelCatalogTests(unittest.TestCase):
    def test_pinned_model_matches_requested_repository(self):
        model=MODEL_CATALOG[0]
        self.assertEqual(model['repository'],'JonathanColetti/Qwen3.8-27B-Uncensored-GGUF')
        self.assertEqual(model['bytes'],16810714528)
        self.assertRegex(model['revision'],r'^[0-9a-f]{40}$')
        self.assertRegex(model['sha256'],r'^[0-9a-f]{64}$')

    def test_download_is_verified_reused_and_rejects_a_changed_file(self):
        content=b'GGUF'+b'local model download fixture'*80
        model={**MODEL_CATALOG[0],'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as folder,patch('backend.ai_models.MODEL_CATALOG',(model,)):
                downloads=Downloads(folder);models=AIModels(downloads)
                with patch.object(models,'url',return_value=f'http://127.0.0.1:{server.server_port}/model'):
                    self.assertFalse(models.status()['models'][0]['ready'])
                    with self.assertRaises(PermissionError):models.start(model['id'])
                    with self.assertRaises(ValueError):models.specification(model['id'])
                    models.start(model['id'],True);deadline=time.time()+5
                    while not models.status()['models'][0]['ready'] and time.time()<deadline:time.sleep(.02)
                    spec=models.specification(model['id']);self.assertEqual(Path(spec['path']).read_bytes(),content)
                    models.start(model['id'],True);self.assertEqual(len(downloads.snapshot()['items']),1)
                    self.assertEqual(models.specifications()[0]['id'],model['id'])
                    Path(spec['path']).write_bytes(content+b'corruption')
                    self.assertFalse(models.status()['models'][0]['ready'])
                    with self.assertRaises(ValueError):models.specification(model['id'])
                    downloads.shutdown()
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
