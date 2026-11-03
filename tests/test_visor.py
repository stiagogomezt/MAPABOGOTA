import os, subprocess, sys, time, unittest, http.server, socketserver, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class VisorSmokeTests(unittest.TestCase):
    def test_smoke_page_loads(self):
        os.chdir(ROOT / "web")
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", 8099), http.server.SimpleHTTPRequestHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        time.sleep(1)
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:8099/", timeout=10)
            html = resp.read().decode("utf-8")
            self.assertIn("<canvas", html)
            self.assertIn("three", html)
        finally:
            httpd.shutdown()
            os.chdir(ROOT)

if __name__ == "__main__":
    unittest.main()