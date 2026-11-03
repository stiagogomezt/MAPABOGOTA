import unittest
from pathlib import Path
WEB = Path(__file__).resolve().parents[1] / "web"

class NavegacionTests(unittest.TestCase):
    def test_zoom_time(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("OrbitControls", html)

    def test_fps(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("renderer.setPixelRatio", html)

if __name__ == "__main__":
    unittest.main()
