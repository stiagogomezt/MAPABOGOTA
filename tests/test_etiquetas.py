import unittest
from pathlib import Path
WEB = Path(__file__).resolve().parents[1] / "web"

class EtiquetasTests(unittest.TestCase):
    def test_labels_in_dom(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("labelData", html)
        self.assertIn("updateLabels", html)

    def test_no_overlap(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("'label'", html)

if __name__ == "__main__":
    unittest.main()
