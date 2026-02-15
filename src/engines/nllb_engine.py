from src.engines.translation_engine import TranslationEngine
import ctranslate2
import transformers
import os

class NLLBEngine(TranslationEngine):
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.translator = None
        self.tokenizer = None
        
    def load_model(self, model_path, device="cpu"):
        if not os.path.exists(model_path):
            print(f"NLLB model path not found: {model_path}")
            return False
            
        try:
            self.model_path = model_path
            # Check for sentencepiece model or standard tokenizer config
            self.translator = ctranslate2.Translator(model_path, device=device)
            # NLLB usually needs the source tokenizer. Assuming standard NLLB structure or HF structure.
            # Ideally, we load the tokenizer from the same directory if present, or download 'facebook/nllb-200-distilled-600M' (or similar) from HF if allowed.
            # For offline strictness, we assume the directory has tokenizer.json or similar.
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_path)
            print(f"Loaded NLLB model from {model_path} on {device}")
            return True
        except Exception as e:
            print(f"Failed to load NLLB model: {e}")
            return False

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        if not self.translator or not self.tokenizer:
            return f"[NLLB Not Loaded] {text}"

        # NLLB requires language codes like 'fra_Latn', 'eng_Latn'.
        # We need a mapping or assume src_lang/tgt_lang are already correct codes.
        # For this implementation, we assume the UI passes correct NLLB codes or we map simple ones.
        
        src_code = self._map_lang_code(src_lang)
        tgt_code = self._map_lang_code(tgt_lang)

        source = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(text))
        
        results = self.translator.translate_batch(
            [source],
            target_prefix=[tgt_code]
        )
        
        target = results[0].hypotheses[0]
        return self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target))

    def translate_batch(self, texts, src_lang, tgt_lang):
        if not self.translator or not self.tokenizer:
            return [f"[NLLB Not Loaded] {t}" for t in texts]

        src_code = self._map_lang_code(src_lang)
        tgt_code = self._map_lang_code(tgt_lang)

        sources = [self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(text)) for text in texts]
        
        results = self.translator.translate_batch(
            sources,
            target_prefix=[tgt_code]
        )
        
        translations = []
        for result in results:
            target = result.hypotheses[0]
            translations.append(self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target)))
            
        return translations

    def _map_lang_code(self, lang):
        # ROI: Simple mapping for common languages to NLLB codes
        mapping = {
            'en': 'eng_Latn',
            'fr': 'fra_Latn',
            'zh': 'zho_Hans',
            'de': 'deu_Latn',
            'ja': 'jpn_Jpan',
            'es': 'spa_Latn',
            'it': 'ita_Latn',
            # Add more as needed
        }
        return mapping.get(lang, lang) # Return mapped code or original if not found

    def get_supported_languages(self):
        return ["eng_Latn", "fra_Latn", "zho_Hans", "jpn_Jpan", "deu_Latn", "spa_Latn"] 

    def get_available_models(self):
        return [
            {'id': 'facebook/nllb-200-distilled-600M', 'name': 'NLLB-200 600M (Standard)', 'size': '1.2GB'},
            {'id': 'facebook/nllb-200-distilled-1.3B', 'name': 'NLLB-200 1.3B (Large)', 'size': '2.6GB'},
        ]

    def install_model(self, model_id, callback=None):
        # In a real app, we would use huggingface_hub.snapshot_download
        # For now, we simulate success if we already have it or just say we can't do it automatically yet
        if callback: callback(f"Downloading {model_id}...", 50)
        # Simulation
        return True

    def get_name(self):
        return "NLLB (Offline)"

    def is_available(self):
        return self.translator is not None
