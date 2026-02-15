from abc import ABC, abstractmethod

class TranslationEngine(ABC):
    @abstractmethod
    def translate(self, text, src_lang, tgt_lang, context=None):
        """Translates a single text segment. context is optional."""
        pass

    @abstractmethod
    def translate_batch(self, texts, src_lang, tgt_lang):
        """Translates a list of text segments."""
        pass

    @abstractmethod
    def get_supported_languages(self):
        """Returns a list of supported language codes."""
        pass
    
    @abstractmethod
    def get_name(self):
        """Returns the display name of the engine."""
        pass
    
    @abstractmethod
    def is_available(self):
        """Returns True if the engine is ready to use (e.g. models loaded)."""
        pass
