import json, os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

CRITICOS = {"REQ-COORD", "REQ-ALTITUD", "REQ-ORIENTACION", "REQ-PUBLICACION", "REQ-VISOR"}

class TestReqCoord(unittest.TestCase):
    def test_req_coord_pyproj(self):
        import pyproj
        t = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:9377", always_xy=True)
        x, y = t.transform(-74.0721, 4.5981)
        self.assertTrue(4.8e6 < x < 4.95e6)

    def test_req_coord_click(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("proj4('EPSG:9377','EPSG:4326'", html)
        self.assertIn("EPSG:9377: E=", html)
        self.assertIn("Copiar", html)

class TestReqAltitud(unittest.TestCase):
    def test_req_altitud_range(self):
        hr = ROOT / "data" / "processed" / "terrain" / "height_range.json"
        self.assertTrue(hr.exists())
        d = json.loads(hr.read_text())
        self.assertLess(d["min_m"], d["max_m"])

    def test_req_altitud_click(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("p.z/(1.5*exag)+1295.2", html)

class TestReqFichaCatastral(unittest.TestCase):
    def test_req_ficha_catastral(self):
        self.fail("Requiere PMTiles + Playwright")

class TestReqEtiquetas(unittest.TestCase):
    def test_req_etiquetas(self):
        self.fail("Requiere Playwright")

class TestReqEscala(unittest.TestCase):
    def test_req_escala(self):
        self.fail("Requiere Playwright")

class TestReqHd(unittest.TestCase):
    def test_req_hd_pixel_ratio(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("setPixelRatio", html)

class TestReqCosturas(unittest.TestCase):
    def test_req_costuras(self):
        self.fail("Requiere analisis de imagen")

class TestReqSombras(unittest.TestCase):
    def test_req_sombras(self):
        self.fail("Requiere Playwright")

class TestReqNavegacion(unittest.TestCase):
    def test_req_navegacion(self):
        self.fail("Requiere Playwright")

class TestReqDiseno(unittest.TestCase):
    def test_req_diseno(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("--", html)  # CSS variables

class TestReqOrganizacion(unittest.TestCase):
    def test_req_organizacion(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("Capas", html)

class TestReqAyuda(unittest.TestCase):
    def test_req_ayuda(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("help", html.lower())

class TestReqOrientacion(unittest.TestCase):
    def test_req_orientacion(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("terrain.scale.x=-1", html)
        self.assertIn("camera.up.set(0,1,0)", html)

class TestReqPublicacion(unittest.TestCase):
    def test_req_publicacion(self):
        import subprocess
        r = subprocess.run(["python", "scripts/audit_web.py"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
