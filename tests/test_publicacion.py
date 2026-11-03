import os
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
LIMIT_TOTAL = 300 * 1024 * 1024
LIMIT_FILE = 50 * 1024 * 1024

class PublicationSizeTests(unittest.TestCase):
    def test_web_total_below_300mb(self):
        total = sum(f.stat().st_size for f in WEB.rglob("*") if f.is_file())
        self.assertLessEqual(total, LIMIT_TOTAL, f"web/ pesa {total} bytes (>300 MB)")

    def test_no_file_over_50mb(self):
        big = [str(f.relative_to(WEB)) for f in WEB.rglob("*") if f.is_file() and f.stat().st_size > LIMIT_FILE]
        self.assertEqual(big, [], f"Archivos >50 MB: {big}")

if __name__ == "__main__":
    unittest.main()
