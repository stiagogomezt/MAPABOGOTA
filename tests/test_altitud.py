import json, unittest
from pathlib import Path
import rasterio, numpy as np

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MDT = ROOT / "data" / "processed" / "terrain" / "mdt_fused_9377_5m.tif"
HR = ROOT / "web" / "terrain" / "height_range.json"
if not HR.exists():
    HR = ROOT / "data" / "processed" / "terrain" / "height_range.json"

class AltitudTests(unittest.TestCase):
    def test_height_range_exists(self):
        self.assertTrue(HR.exists(), "height_range.json no existe")
        data = json.loads(HR.read_text())
        self.assertIn("min_m", data)
        self.assertIn("max_m", data)
        self.assertLess(data["min_m"], data["max_m"])

    def test_mdt_in_range(self):
        if not MDT.exists():
            self.skipTest("MDT no disponible en CI")
        with rasterio.open(MDT) as src:
            a = src.read(1).astype("float32")
            a[a == src.nodata] = np.nan
            valid = a[~np.isnan(a)]
            hr = json.loads(HR.read_text())
            self.assertAlmostEqual(valid.min(), hr["min_m"], delta=1.0)
            self.assertAlmostEqual(valid.max(), hr["max_m"], delta=1.0)

    def test_click_altitude_no_exaggeration(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("p.z/(1.5*exag)+1295.2", html)

if __name__ == "__main__":
    unittest.main()
