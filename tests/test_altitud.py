import json, unittest
from pathlib import Path
import rasterio, numpy as np

ROOT = Path(__file__).resolve().parents[1]
MDT = ROOT / "data" / "processed" / "terrain" / "mdt_fused_9377_5m.tif"
HR = ROOT / "data" / "processed" / "terrain" / "height_range.json"

class AltitudTests(unittest.TestCase):
    def test_height_range_exists(self):
        self.assertTrue(HR.exists(), "height_range.json no existe")
        data = json.loads(HR.read_text())
        self.assertIn("min_m", data)
        self.assertIn("max_m", data)
        self.assertLess(data["min_m"], data["max_m"])

    def test_mdt_in_range(self):
        with rasterio.open(MDT) as src:
            a = src.read(1).astype("float32")
            a[a == src.nodata] = np.nan
            valid = a[~np.isnan(a)]
            hr = json.loads(HR.read_text())
            self.assertAlmostEqual(valid.min(), hr["min_m"], delta=1.0)
            self.assertAlmostEqual(valid.max(), hr["max_m"], delta=1.0)

    def test_click_altitude_no_exaggeration(self):
        self.fail("Requiere servidor local + Playwright")

if __name__ == "__main__":
    unittest.main()
