import logging
from src.engines.translation_engine import TranslationEngine
from src.core.glossary_applier import GlossaryApplier
from src.core.tag_manager import TagManager

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

    def supports_tags(self):
        return False
        
    def load_model(self, model_path=None, device="cpu"):
        # No model to load for web API
        return True

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None, **kwargs):
        if not HAS_DEEP_TRANSLATOR: 
            import logging
            logging.error("deep-translator not installed.")
            return text
        if not text: return ""

        try:
            tm = TagManager()
            safe_text, tags_map = tm.protect_tags_for_nmt(text)
            
            # Handle 'auto' source
            src = src_lang if src_lang and src_lang != 'auto' else 'auto'
            # GoogleTranslator expects standard codes
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=src, target=tgt_lang)
            translation = translator.translate(safe_text)
            
            # Restore tags
            translation = tm.restore_tags_from_nmt(translation, tags_map)
            
            if glossary_terms:
                applier = GlossaryApplier(glossary_terms)
                translation = applier.apply(translation)
                
            return translation
        except Exception as e:
            import logging
            logging.error(f"Google Translate Error: {e}")
            return text
    def translate_batch(self, texts, src_lang, tgt_lang, glossary_terms=None, **kwargs):
        if not HAS_DEEP_TRANSLATOR: return texts
        if not texts: return []
        
        if isinstance(texts, str): texts = [texts]
        
        translations = []
        for text in texts:
            translations.append(self.translate(text, src_lang, tgt_lang, context=None, glossary_terms=glossary_terms, **kwargs))
        return translations
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
