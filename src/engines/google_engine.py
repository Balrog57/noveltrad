import logging
from src.engines.translation_engine import TranslationEngine

try:
    from deep_translator import GoogleTranslator
    HAS_DEEP_TRANSLATOR = True
except ImportError:
    HAS_DEEP_TRANSLATOR = False
    logging.warning("deep-translator library not found. Google Engine will be unavailable.")

class GoogleEngine(TranslationEngine):
    def __init__(self):
        super().__init__()
        self._name = "Google Translate (Web)"

    def load_model(self, model_path=None, device="cpu"):
        # No model to load for web API
        return True

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        if not HAS_DEEP_TRANSLATOR: 
            logging.error("deep-translator not installed.")
            return text
        if not text: return ""

        # Basic glossary handling (replace source with target before translation)
        # Note: This is naive and might break context or capitalization
        temp_text = text
        if glossary_terms:
            # Sort by length descending to replace longest terms first
            sorted_terms = sorted(glossary_terms.keys(), key=len, reverse=True)
            for src_term in sorted_terms:
                if src_term in temp_text:
                    temp_text = temp_text.replace(src_term, glossary_terms[src_term])
        
        try:
            # Handle 'auto' source
            src = src_lang if src_lang and src_lang != 'auto' else 'auto'
            # GoogleTranslator expects standard codes (en, fr, etc.)
            translator = GoogleTranslator(source=src, target=tgt_lang)
            return translator.translate(temp_text)
        except Exception as e:
            logging.error(f"Google Translate Error: {e}")
            return text

    def translate_batch(self, texts, src_lang, tgt_lang):
        if not HAS_DEEP_TRANSLATOR: return texts
        if not texts: return []
        
        if isinstance(texts, str): texts = [texts]
        
        try:
            src = src_lang if src_lang and src_lang != 'auto' else 'auto'
            translator = GoogleTranslator(source=src, target=tgt_lang)
            return translator.translate_batch(texts)
        except Exception as e:
            logging.error(f"Google Batch Translate Error: {e}")
            return texts

    def get_supported_languages(self):
        if not HAS_DEEP_TRANSLATOR: return []
        try:
            # deep_translator returns dict {name: code}
            return list(GoogleTranslator().get_supported_languages(as_dict=True).values())
        except:
            return ['en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'ja', 'zh-CN'] # Fallback

    def get_name(self):
        return self._name

    def is_available(self):
        return HAS_DEEP_TRANSLATOR

    def get_available_models(self):
        return []

    def install_model(self, model_id, callback=None):
        return False
