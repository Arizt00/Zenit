"""Desktop windows must be able to queue their parallel module requests."""
import http.client
from pathlib import Path
import socket
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import LumenServer


class ModuleBurstTests(unittest.TestCase):
    def test_queued_window_module_requests_are_served_without_dropped_connections(self):
        server=LumenServer(0,SimpleNamespace(project=ROOT))
        connections=[];thread=None
        try:
            # Queue the burst before accepting it: this is deterministic even
            # on a fast machine. The old backlog of five fails during connect.
            for _ in range(16):
                connections.append(socket.create_connection(server.server_address,timeout=1))
            for conn in connections:
                conn.sendall((f'GET /src/team-view.js HTTP/1.0\r\nHost: 127.0.0.1:{server.server_port}\r\n\r\n').encode())
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            for conn in connections:
                conn.settimeout(5)
                response=http.client.HTTPResponse(conn);response.begin()
                self.assertEqual(response.status,200)
                self.assertEqual(response.getheader('Content-Type'),'text/javascript; charset=utf-8')
                self.assertEqual(response.read(),(ROOT/'web/src/team-view.js').read_bytes())
                response.close()
        finally:
            for conn in connections:conn.close()
            if thread:server.shutdown();thread.join(timeout=5)
            server.server_close()


if __name__=='__main__':unittest.main()
