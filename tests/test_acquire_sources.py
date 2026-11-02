import unittest

from scripts.acquire_sources import esri_geometry, safe_fields, scale_range


class ArcGISConversionTests(unittest.TestCase):
    def test_polygon_mask_converts_to_esri_rings(self) -> None:
        polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        }
        result = esri_geometry(polygon)
        self.assertEqual(result["rings"], polygon["coordinates"])
        self.assertEqual(result["spatialReference"]["wkid"], 4326)

    def test_sensitive_fields_are_excluded(self) -> None:
        layer = {
            "fields": [
                {"name": "OBJECTID", "type": "esriFieldTypeOID"},
                {"name": "CODIGO", "type": "esriFieldTypeString"},
                {"name": "PROPIETARIO", "type": "esriFieldTypeString"},
                {"name": "SHAPE", "type": "esriFieldTypeGeometry"},
            ]
        }
        self.assertEqual(safe_fields(layer), ["OBJECTID", "CODIGO"])

    def test_zero_arcgis_scale_limits_are_reported_as_unspecified(self) -> None:
        self.assertIn("No declarada", scale_range({"minScale": 0, "maxScale": 0}))


if __name__ == "__main__":
    unittest.main()
