import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"

class DisenoTests(unittest.TestCase):
    def test_no_native_controls_unstyled(self):
        # Check that index.html does not use default <select> without class
        html = (WEB / "index.html").read_text(encoding="utf-8")
        # Every <select> must have a style or class attribute
        import re
        for m in re.finditer(r"<select[^>]*>", html):
            tag = m.group(0)
            self.assertTrue("style=" in tag or "class=" in tag, f"Select sin estilo: {tag}")

    def test_localidades_texture_removed(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        # The texture card list should not include "Localidades" as a texture
        self.assertNotIn('value="localidades"', html)

if __name__ == "__main__":
    unittest.main()
