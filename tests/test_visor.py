import os, subprocess, sys, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = "node"
NODE_PATH = os.pathsep.join([
    str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules"),
    "/usr/lib/node_modules",
    "/usr/local/lib/node_modules",
])

class VisorSmokeTests(unittest.TestCase):
    def test_smoke_canvas_not_black(self):
        # start server
        import http.server, socketserver, threading
        os.chdir(ROOT / "web")
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", 8099), http.server.SimpleHTTPRequestHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        time.sleep(1)
        env = dict(os.environ, NODE_PATH=NODE_PATH)
        r = subprocess.run([NODE, str(ROOT / "scripts" / "smoke_test.js")],
                           capture_output=True, text=True, timeout=120, env=env,
                           cwd=str(ROOT))
        httpd.shutdown()
        os.chdir(ROOT)
        print(r.stdout)
        print(r.stderr)
        self.assertEqual(r.returncode, 0, f"Smoke test failed: {r.stdout}\n{r.stderr}")

if __name__ == "__main__":
    unittest.main()
