import unittest
from unittest.mock import MagicMock, patch
from src.engines.google_engine import GoogleEngine

class TestGoogleEngine(unittest.TestCase):
    @patch('src.engines.google_engine.GoogleTranslator')
    @patch('src.engines.google_engine.HAS_DEEP_TRANSLATOR', True)
    def test_translate_success(self, MockTranslator):
        # Mock successful translation
        mock_instance = MockTranslator.return_value
        mock_instance.translate.return_value = "Bonjour"
        
        engine = GoogleEngine()
        result = engine.translate("Hello", "en", "fr")
        
        self.assertEqual(result, "Bonjour")
        MockTranslator.assert_called_with(source="en", target="fr")

    @patch('src.engines.google_engine.GoogleTranslator')
    @patch('src.engines.google_engine.HAS_DEEP_TRANSLATOR', True)
    def test_translate_auto_source(self, MockTranslator):
        mock_instance = MockTranslator.return_value
        mock_instance.translate.return_value = "Bonjour"
        
        engine = GoogleEngine()
        engine.translate("Hello", None, "fr") # auto
        
        MockTranslator.assert_called_with(source="auto", target="fr")

    @patch('src.engines.google_engine.HAS_DEEP_TRANSLATOR', True)
    def test_translate_empty(self):
        engine = GoogleEngine()
        self.assertEqual(engine.translate("", "en", "fr"), "")

    @patch('src.engines.google_engine.HAS_DEEP_TRANSLATOR', False)
    def test_unavailable(self):
        engine = GoogleEngine()
        self.assertFalse(engine.is_available())
        # Should return original text if unavailable
        self.assertEqual(engine.translate("Hello", "en", "fr"), "Hello")
