import json, subprocess, unittest
from pathlib import Path
import pyproj

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
GEOREF = ROOT / "data" / "processed" / "terrain" / "georef.json"

REFS = {
    "Plaza de Bolivar": (-74.0721, 4.5981),
    "Monserrate": (-74.0586, 4.6056),
    "Aeropuerto El Dorado": (-74.1433, 4.7016),
}

class CoordenadasTests(unittest.TestCase):
    def test_pyproj_conversion(self):
        t = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:9377", always_xy=True)
        for name, (lon, lat) in REFS.items():
            x, y = t.transform(lon, lat)
            self.assertTrue(4.8e6 < x < 4.95e6, f"{name} X fuera de rango: {x}")
            self.assertTrue(2.0e6 < y < 2.15e6, f"{name} Y fuera de rango: {y}")

    def test_click_returns_real_coords(self):
        # Placeholder: requires Playwright. Marked as not verifiable in headless CI.
        self.fail("Requiere servidor local + Playwright")

if __name__ == "__main__":
    unittest.main()
