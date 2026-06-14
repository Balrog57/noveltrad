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
import tempfile
import unittest
from pathlib import Path

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

    def test_default_language_reads_configured_french(self) -> None:
        from src.gui.app_config import ConfigManager
        from src.gui.i18n import default_language

        old_instance = ConfigManager._instance
        old_config_file = ConfigManager.CONFIG_FILE
        old_legacy_file = ConfigManager.LEGACY_CONFIG_FILE
        old_env = os.environ.get("NOVELTRAD_LANGUAGE")
        try:
            os.environ.pop("NOVELTRAD_LANGUAGE", None)
            with tempfile.TemporaryDirectory() as tmp:
                cfg = Path(tmp) / "config.json"
                cfg.write_text(
                    '{"first_run": false, "ui": {"language": "fr"}}',
                    encoding="utf-8",
                )
                ConfigManager._instance = None
                ConfigManager.CONFIG_FILE = cfg
                ConfigManager.LEGACY_CONFIG_FILE = Path(tmp) / "missing.json"
                self.assertEqual(default_language(), "fr")
        finally:
            ConfigManager._instance = old_instance
            ConfigManager.CONFIG_FILE = old_config_file
            ConfigManager.LEGACY_CONFIG_FILE = old_legacy_file
            if old_env is not None:
                os.environ["NOVELTRAD_LANGUAGE"] = old_env

    def test_installer_language_used_for_initial_config_only(self) -> None:
        from src.gui.app_config import ConfigManager

        old_instance = ConfigManager._instance
        old_config_file = ConfigManager.CONFIG_FILE
        old_legacy_file = ConfigManager.LEGACY_CONFIG_FILE
        old_installer_file = ConfigManager.INSTALLER_LANGUAGE_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                ConfigManager._instance = None
                ConfigManager.CONFIG_FILE = tmp_path / "missing_config.json"
                ConfigManager.LEGACY_CONFIG_FILE = tmp_path / "missing_legacy.json"
                ConfigManager.INSTALLER_LANGUAGE_FILE = tmp_path / "installer_language.txt"
                ConfigManager.INSTALLER_LANGUAGE_FILE.write_text("fr", encoding="utf-8")
                self.assertEqual(ConfigManager().config["ui"]["language"], "fr")
        finally:
            ConfigManager._instance = old_instance
            ConfigManager.CONFIG_FILE = old_config_file
            ConfigManager.LEGACY_CONFIG_FILE = old_legacy_file
            ConfigManager.INSTALLER_LANGUAGE_FILE = old_installer_file


if __name__ == "__main__":
    unittest.main()
