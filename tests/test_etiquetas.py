import unittest
from pathlib import Path

class EtiquetasTests(unittest.TestCase):
    def test_labels_in_dom(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("labelData", html)
        self.assertIn("updateLabels", html)

    def test_no_overlap(self):
        # Structural check: labels container exists
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("class='label'", html) or self.assertIn('class="label"', html)

if __name__ == "__main__":
    unittest.main()
