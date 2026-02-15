from src.engines.translation_engine import TranslationEngine
from openai import OpenAI
from typing import List
import json

GENRE_PROMPTS = {
    "xianxia": """You are an expert in Chinese fantasy novels (Xianxia). Identify:
- Cultivation realms (ex: Foundation Establishment, Soul Formation)
- Cultivation techniques and methods
- Magical items and weapons
- Sects and organizations
- Character names and titles
- Cultural concepts (Dao, Yin-Yang, etc.)""",
    
    "scifi": """You are an expert in Science Fiction. Identify:
- Technology terms and devices
- Spaceships and vehicles
- Planets and locations
- Alien species and factions
- Scientific concepts""",
    
    "fantasy": """You are an expert in Fantasy literature. Identify:
- Magical creatures and beings
- Spells and enchantments
- Locations and realms
- Artifacts and magical items""",
    
    "romance": """You are an expert in Romance novels. Identify:
- Character names
- Relationship titles
- Emotional concepts""",
    
    "general": """You are a glossary extraction tool. Identify:
- Proper names (characters, places)
- Organizations
- Key terms and concepts"""
}

TRANSLATION_STYLE_GUIDES = {
    "xianxia": """Rules for French Xianxia Translation:
1. Tone: Formal and archaic (vouvoiement between peers unless intimate, formal speech).
2. Tenses: Use 'Passé Simple' for actions and 'Imparfait' for descriptions and ongoing states.
3. Terminology: Strict adherence to existing glossary.
4. Imagery: Maintain the heavy metaphorical style of cultivation descriptions.""",
    
    "scifi": "Tone: Technical and precise. Maintain consistent naming for futuristic technologies.",
    "fantasy": "Tone: Epic and descriptive.",
}

# Comprehensive mapping from ISO codes to full names (from TranslateGemma template)
LANGUAGE_NAMES = {
    "aa": "Afar", "ab": "Abkhazian", "af": "Afrikaans", "ak": "Akan", "am": "Amharic", "an": "Aragonese", 
    "ar": "Arabic", "as": "Assamese", "az": "Azerbaijani", "ba": "Bashkir", "be": "Belarusian", "bg": "Bulgarian", 
    "bm": "Bambara", "bn": "Bengali", "bo": "Tibetan", "br": "Breton", "bs": "Bosnian", "ca": "Catalan", 
    "ce": "Chechen", "co": "Corsican", "cs": "Czech", "cv": "Chuvash", "cy": "Welsh", "da": "Danish", 
    "de": "German", "dv": "Divehi", "dz": "Dzongkha", "ee": "Ewe", "el": "Greek", "en": "English", 
    "eo": "Esperanto", "es": "Spanish", "et": "Estonian", "eu": "Basque", "fa": "Persian", "ff": "Fulah", 
    "fi": "Finnish", "fo": "Faroese", "fr": "French", "fy": "Western Frisian", "ga": "Irish", "gd": "Scottish Gaelic", 
    "gl": "Galician", "gn": "Guarani", "gu": "Gujarati", "gv": "Manx", "ha": "Hausa", "he": "Hebrew", "hi": "Hindi", 
    "hr": "Croatian", "ht": "Haitian", "hu": "Hungarian", "hy": "Armenian", "ia": "Interlingua", "id": "Indonesian", 
    "ie": "Interlingue", "ig": "Igbo", "ii": "Sichuan Yi", "ik": "Inupiaq", "io": "Ido", "is": "Icelandic", 
    "it": "Italian", "iu": "Inuktitut", "ja": "Japanese", "jv": "Javanese", "ka": "Georgian", "ki": "Kikuyu", 
    "kk": "Kazakh", "kl": "Kalaallisut", "km": "Central Khmer", "kn": "Kannada", "ko": "Korean", "ks": "Kashmiri", 
    "ku": "Kurdish", "kw": "Cornish", "ky": "Kyrgyz", "la": "Latin", "lb": "Luxembourgish", "lg": "Ganda", 
    "ln": "Lingala", "lo": "Lao", "lt": "Lithuanian", "lu": "Luba-Katanga", "lv": "Latvian", "mg": "Malagasy", 
    "mi": "Maori", "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi", "ms": "Malay", 
    "mt": "Maltese", "my": "Burmese", "nb": "Norwegian Bokmål", "nd": "North Ndebele", "ne": "Nepali", 
    "nl": "Dutch", "nn": "Norwegian Nynorsk", "no": "Norwegian", "nr": "South Ndebele", "nv": "Navajo", 
    "ny": "Chichewa", "oc": "Occitan", "om": "Oromo", "or": "Oriya", "os": "Ossetian", "pa": "Punjabi", 
    "pl": "Polish", "ps": "Pashto", "pt": "Portuguese", "qu": "Quechua", "rm": "Romansh", "rn": "Rundi", 
    "ro": "Romanian", "ru": "Russian", "rw": "Kinyarwanda", "sa": "Sanskrit", "sc": "Sardinian", "sd": "Sindhi", 
    "se": "Northern Sami", "sg": "Sango", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "sn": "Shona", 
    "so": "Somali", "sq": "Albanian", "sr": "Serbian", "ss": "Swati", "st": "Southern Sotho", "su": "Sundanese", 
    "sv": "Swedish", "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "tg": "Tajik", "th": "Thai", "ti": "Tigrinya", 
    "tk": "Turkmen", "tl": "Tagalog", "tn": "Tswana", "to": "Tonga", "tr": "Turkish", "ts": "Tsonga", "tt": "Tatar", 
    "ug": "Uyghur", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek", "ve": "Venda", "vi": "Vietnamese", "vo": "Volapük", 
    "wa": "Walloon", "wo": "Wolof", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", "za": "Zhuang", "zh": "Chinese", 
    "zh-Hans": "Chinese", "zh-Hant": "Chinese", "zu": "Zulu"
}

# Inverted mapping to find code by name
NAME_TO_CODE = {v.lower(): k for k, v in LANGUAGE_NAMES.items()}
# Add common variants
NAME_TO_CODE.update({
    "chinese": "zh",
    "french": "fr",
    "english": "en",
    "spanish": "es",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "german": "de"
})

def get_language_code(lang_str):
    """Helper to convert language name or code to official ISO code."""
    if not lang_str: return "en"
    clean = lang_str.lower().strip().replace("_", "-")
    # If it's already a known code
    if clean in LANGUAGE_NAMES:
        return clean
    # If it's a known name
    if clean in NAME_TO_CODE:
        return NAME_TO_CODE[clean]
    # Default fallback
    return clean[:2]

class LLMEngine(TranslationEngine):
    def __init__(self, api_key="lm-studio", base_url="http://localhost:1234/v1", model="gemma-3-12b"):
        self.client = None
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        if api_key:
            self.init_client(api_key, base_url)

    def init_client(self, api_key, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def load_model(self, model_path, device="cpu"):
        self.model = model_path
        return True

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None, custom_instructions=None, genre=None):
        if not self.client:
            return f"[LLM Config Missing] {text}"
            
        system_prompt = f"Maintain novel flow and tone (Project: NovelTrad)."
        
        if genre and genre in TRANSLATION_STYLE_GUIDES:
            system_prompt += f"\nStyle Guide: {TRANSLATION_STYLE_GUIDES[genre]}"
            
        if custom_instructions:
            system_prompt += f"\nCustom instructions: {custom_instructions}"
        
        if glossary_terms:
            glossary_txt = ", ".join([f"{k}:{v}" for k, v in glossary_terms.items()])
            system_prompt += f"\nGlossary: {glossary_txt}"
            
        src_code = get_language_code(src_lang)
        tgt_code = get_language_code(tgt_lang)

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            # Combined text with metadata for the model
            full_text = ""
            if system_prompt:
                full_text += f"[[Instructions: {system_prompt}]]\n"
            if context:
                full_text += f"[[Context: {context}]]\n"
            full_text += text

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": src_code,
                            "target_lang_code": tgt_code,
                            "text": full_text
                        }
                    ]
                }
            ]
        else:
            user_prompt = f"Context:\n{context}\n\nTranslate:\n{text}" if context else f"{text}"
            src_name = LANGUAGE_NAMES.get(src_code, src_lang)
            tgt_name = LANGUAGE_NAMES.get(tgt_code, tgt_lang)
            messages = [
                {"role": "system", "content": f"{system_prompt}\nTranslate from {src_name} to {tgt_name}."},
                {"role": "user", "content": user_prompt}
            ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def generate_glossary(self, text, src_lang="Chinese", tgt_lang="French", genre="general"):
        """Generate glossary terms from text using LLM."""
        if not self.client:
            import json
            return json.dumps([])

        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        src_code = get_language_code(src_lang)
        tgt_code = get_language_code(tgt_lang)

        system_prompt = f"{genre_prompt}\nExtract terms as JSON array: [{{'source': 'term', 'target': 'translation', 'category': 'Name'}}]"
        
        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": src_code,
                            "target_lang_code": tgt_code,
                            "text": f"[[TASK: GLOSSARY EXTRACTION]]\n{system_prompt}\n\n{text[:3000]}"
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text:\n{text[:3000]}"}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1
            )
            return self._extract_json(response.choices[0].message.content)
        except Exception as e:
            print(f"Glossary Gen Error: {e}")
            import json
            return json.dumps([])

    def generate_glossary_incremental(self, text, existing_terms, src_lang="Chinese", tgt_lang="French", genre="general"):
        """Generate glossary incrementally, avoiding duplicates."""
        if not self.client:
            import json
            return json.dumps([])
            
        existing_list = existing_terms[:50] if isinstance(existing_terms, list) else []
        existing_str = ", ".join([f"{e.get('source', e.get('source_term', ''))}:{e.get('target', e.get('target_term', ''))}" for e in existing_list])
        
        src_code = get_language_code(src_lang)
        tgt_code = get_language_code(tgt_lang)
        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        system_prompt = f"{genre_prompt}\nExtract NEW terms (Not in: {existing_str})."

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": src_code,
                            "target_lang_code": tgt_code,
                            "text": f"[[TASK: INCREMENTAL GLOSSARY]]\n{system_prompt}\n\nJSON Output required.\n\n{text[:3000]}"
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": f"{system_prompt}\nReturn ONLY new terms as JSON array."},
                {"role": "user", "content": f"New text:\n{text[:3000]}"}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1
            )
            return self._extract_json(response.choices[0].message.content)
        except Exception as e:
            print(f"Incremental Glossary Error: {e}")
            import json
            return json.dumps([])

    def _extract_json(self, content):
        """Helper to extract JSON from LLM response."""
        if not content:
            import json
            return json.dumps([])
        import json
        import re
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Simple extraction if still contains text around it
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group()
            
        try:
            # Validate if it's correct JSON
            parsed = json.loads(content)
            return json.dumps(parsed, ensure_ascii=False)
        except:
            return json.dumps([])

    def refine_translation(self, source_text, translated_text, src_lang="en", tgt_lang="fr", glossary_terms=None):
        """Refine/Edit AI - improve machine translation using LLM."""
        if not self.client:
            return translated_text
            
        system_prompt = f"Expert Editor. Improve fluency/naturalness in {tgt_lang}. Keep consistent terminology. No explanations."
        if glossary_terms:
            glos = ", ".join([f"{k}:{v}" for k, v in glossary_terms.items()])
            system_prompt += f" Glossary: {glos}"
        
        src_code = get_language_code(src_lang)
        tgt_code = get_language_code(tgt_lang)

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": src_code,
                            "target_lang_code": tgt_code,
                            "text": f"[[TASK: REFINE TRANSLATION]]\nInstructions: {system_prompt}\n\nSource: {source_text}\n\nCurrent: {translated_text}\n\nReturn improved version only."
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Source: {source_text}\n\nCurrent: {translated_text}"}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3
            )
            content = response.choices[0].message.content
            return content.strip() if content else translated_text
        except Exception as e:
            print(f"Refine Error: {e}")
            return translated_text
            
    def detect_chapters(self, text):
        """Structure AI - detect chapter boundaries in raw text."""
        if not self.client:
            import json
            return json.dumps([])
            
        system_prompt = "Identify starting lines of chapters. Return JSON list: [{{'title': '...', 'start_line': '...'}}]"
        
        # We use en-fr as dummy codes if we don't know the project context here, 
        # but usually it's better than nothing.
        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": "zh",
                            "target_lang_code": "fr",
                            "text": f"[[TASK: CHAPTER DETECTION]]\n{system_prompt}\n\nText:\n{text[:8000]}"
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text:\n{text[:8000]}"}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1
            )
            return self._extract_json(response.choices[0].message.content)
        except Exception as e:
            print(f"Chapter Detection Error: {e}")
            import json
            return json.dumps([])

    def translate_batch(self, texts, src_lang, tgt_lang):
        return [self.translate(t, src_lang, tgt_lang) for t in texts]

    def get_supported_languages(self):
        return ["Any"]

    def get_name(self):
        return f"LLM ({self.model})"

    def is_available(self):
        return self.client is not None
