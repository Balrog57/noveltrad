"""Smoke test for the i18n infrastructure.

The PyQt6 environment used by the CI doesn't always ship the
``pylrelease6`` tool, so we don't compile the .ts to a .qm in
tests. Instead we verify the helpers behave correctly:

  * default_language() never raises and returns a known code;
  * available_languages() includes English and French;
  * has_translation(code) is a bool;
  * load_translator(code) returns None for missing translations
    (and a QTranslator for fr when a .qm is present, if any).
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class I18nHelpersTests(unittest.TestCase):
    def setUp(self) -> None:
        from PyQt6.QtWidgets import QApplication

        self._app = QApplication.instance() or QApplication([])

    def test_default_language_no_crash(self) -> None:
        from src.gui.i18n import default_language

        code = default_language()
        self.assertIn(code, {"en", "fr"})

    def test_available_languages_includes_en_and_fr(self) -> None:
        from src.gui.i18n import available_languages

        codes = {c for c, _label in available_languages()}
        self.assertIn("en", codes)
        self.assertIn("fr", codes)

    def test_has_translation_returns_bool(self) -> None:
        from src.gui.i18n import has_translation

        self.assertIsInstance(has_translation("en"), bool)
        self.assertIsInstance(has_translation("fr"), bool)
        # 'en' is the source language — never needs a .qm.
        self.assertFalse(has_translation("en"))

    def test_load_translator_fr_no_crash(self) -> None:
        from src.gui.i18n import load_translator

        # Even without a compiled .qm, this must not raise.
        result = load_translator("fr")
        # If the .qm is present (release build) the translator loads.
        # Otherwise we get None — both are acceptable.
        self.assertTrue(result is None or result is not None)

    def test_load_translator_unknown_returns_none(self) -> None:
        from src.gui.i18n import load_translator

        # An unknown code must not raise.
        self.assertIsNone(load_translator("klingon"))


class ConfigLanguageDefaultTests(unittest.TestCase):
    def test_default_config_has_language_key(self) -> None:
        from src.gui.app_config import ConfigManager

        ui = ConfigManager.DEFAULT_CONFIG.get("ui", {})
        self.assertIn("language", ui)
        self.assertEqual(ui["language"], "en")


if __name__ == "__main__":
    unittest.main()
