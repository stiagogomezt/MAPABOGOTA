import unittest

from scripts.audit_web import AccessibilityParser, contrast_ratio


class WebAuditTests(unittest.TestCase):
    def test_skip_link_and_form_accessible_name_are_detected(self) -> None:
        parser = AccessibilityParser()
        parser.feed(
            '<html lang="es"><head><title>Mapa</title></head><body>'
            '<a href="#content">Saltar</a><main id="content"><label for="q">Buscar</label>'
            '<input id="q"><button aria-label="Abrir">+</button></main></body></html>'
        )
        parser.skip_target = bool(parser.fragment_links.intersection(parser.ids))
        self.assertTrue(parser.skip_target)
        self.assertEqual(parser.inputs, [({"id": "q"}, False)])
        self.assertEqual(parser.buttons[0]["aria-label"], "Abrir")

    def test_dark_ui_muted_text_meets_wcag_aa(self) -> None:
        self.assertGreaterEqual(contrast_ratio("#8a9ca3", "#101a22"), 4.5)


if __name__ == "__main__":
    unittest.main()
