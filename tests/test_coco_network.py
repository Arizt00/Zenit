"""Station transport state, verified downloads and cancellation boundaries."""
import hashlib
import io
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from backend.coco_tunnel import InternetTunnel,VERSION


class Response(io.BytesIO):
    status=200


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.features=SimpleNamespace(prefs=SimpleNamespace(directory=self.root),hilo=SimpleNamespace(report=lambda *args:None))
        self.tunnel=InternetTunnel(self.features,'http://127.0.0.1:1234/')
    def tearDown(self):self.tunnel.stop();self.temp.cleanup()
    def test_download_hash_is_checked_before_replacing_cached_bytes(self):
        raw=b'MZ-coco-verified-fixture';asset=('cloudflared-test.exe',hashlib.sha256(raw).hexdigest())
        self.tunnel.directory.mkdir(parents=True);target=self.tunnel.directory/asset[0];target.write_bytes(b'previous')
        with patch('backend.coco_tunnel.ASSETS',{('Windows','AMD64'):asset}),patch('backend.coco_tunnel.platform.system',return_value='Windows'),patch('backend.coco_tunnel.platform.machine',return_value='AMD64'),patch('backend.coco_tunnel.build_opener') as opener:
            opener.return_value.open.return_value=Response(b'bad-download')
            with self.assertRaisesRegex(ValueError,'huella'):self.tunnel.prepare(threading.Event())
            self.assertEqual(target.read_bytes(),b'previous');self.assertEqual(list(target.parent.glob('.cloudflared-*')),[])
            opener.return_value.open.return_value=Response(raw)
            self.assertEqual(self.tunnel.prepare(threading.Event()),target);self.assertEqual(target.read_bytes(),raw)
            opener.reset_mock();self.tunnel.prepare(threading.Event());opener.assert_not_called()
    def test_cancel_before_start_never_downloads_or_launches(self):
        self.tunnel.stop()
        with patch('backend.coco_tunnel.build_opener') as opener,patch('backend.coco_tunnel.subprocess.Popen') as launch:
            with self.assertRaisesRegex(ValueError,'cancelada'):self.tunnel.start(threading.Event())
            opener.assert_not_called();launch.assert_not_called()
        self.assertEqual(self.tunnel.status()['phase'],'failed')
    def test_dead_transport_does_not_advertise_an_active_endpoint(self):
        self.tunnel.phase='ready';self.tunnel.endpoint='https://fixture.trycloudflare.com';self.tunnel.process=SimpleNamespace(poll=lambda:1)
        state=self.tunnel.status();self.assertEqual(state['phase'],'failed');self.assertIsNone(state['endpoint']);self.assertIn('búfer',state['error'])
        self.tunnel.process=None

if __name__=='__main__':unittest.main()
