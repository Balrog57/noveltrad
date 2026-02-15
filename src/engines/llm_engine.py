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
            
        system_prompt = f"You are a professional novel translator. Translate from {src_lang} to {tgt_lang}. Maintain novel flow and tone."
        
        # Apply genre-specific style guide
        if genre and genre in TRANSLATION_STYLE_GUIDES:
            system_prompt += f"\n\nStyle Guide:\n{TRANSLATION_STYLE_GUIDES[genre]}"
            
        if custom_instructions:
            system_prompt += f"\n\nCustom instructions: {custom_instructions}"
        
        if glossary_terms:
            glossary_txt = "\n".join([f"{k} -> {v}" for k, v in glossary_terms.items()])
            system_prompt += f"\n\nUse these terms strictly:\n{glossary_txt}"
            
        user_prompt = f"Context:\n{context}\n\nTranslate:\n{text}" if context else f"Translate:\n{text}"

        # Special handling for Google's TranslateGemma strict template
        is_translategemma = "translategemma" in self.model.lower()
        
        # Ensure lang codes match the 'languages' dict in the Jinja template (lowercase)
        # We use the full code if possible, but fallback to 2 letters if needed
        src_code = src_lang.lower().replace("_", "-")
        tgt_code = tgt_lang.lower().replace("_", "-")

        if is_translategemma:
            # Shift instructions into the text and use list-based content
            full_text = f"[Instructions: {system_prompt}]\n\n{user_prompt}"
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
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            content = response.choices[0].message.content
            # Special check for TranslateGemma: if it returns the template source 
            # instead of text, it's a render failure.
            if content and ("{%-" in content or "start_of_turn" in content and "Prompt Template" in content):
                raise ValueError("Incomplete or failed Jinja rendering in LM Studio")
                
            return content.strip() if content else ""
        except Exception as e:
            error_msg = str(e)
            if is_translategemma:
                # If structured format fails (e.g. Jinja error in LM Studio), fallback to simple text
                print(f"DEBUG: TranslateGemma format failed, falling back to simple text: {error_msg}")
                simple_prompt = f"Translate from {src_lang} to {tgt_lang}:\n\n{system_prompt}\n\n{user_prompt}"
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": simple_prompt}]
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e2:
                    return f"[LLM Error] {error_msg} | Fallback Error: {str(e2)}"
            return f"[LLM Error] {error_msg}"

    def generate_glossary(self, text, src_lang="Chinese", tgt_lang="French", genre="general"):
        """Generate glossary terms from text using LLM."""
        if not self.client:
            import json
            return json.dumps([])

        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        system_prompt = f"{genre_prompt}\nExtract important terms needing consistent translation. Return JSON array with: source, target, category."
        user_prompt = f"Source: {src_lang} -> Target: {tgt_lang}\n\nText:\n{text[:3000]}\n\nJSON array format: [{{'source': 'term', 'target': 'translation', 'category': 'Name'}}]"

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
        existing_str = "\n".join([f"- {e.get('source', e.get('source_term', ''))} -> {e.get('target', e.get('target_term', ''))}" for e in existing_list])
        
        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        system_prompt = f"{genre_prompt}\nExtract NEW terms NOT in existing glossary.\nExisting:\n{existing_str}\n\nReturn ONLY new terms as JSON array."
        user_prompt = f"Source: {src_lang} -> Target: {tgt_lang}\n\nNew text:\n{text[:3000]}\n\nJSON: [{{'source': 'term', 'target': 'translation', 'category': 'Name'}}]"

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
            
        system_prompt = f"""You are an expert translator editor. Your task is to improve the translation quality.
Focus on:
- Improving fluency and naturalness in {tgt_lang}
- Fixing grammar and style issues
- Maintaining the original meaning
- Keeping consistent terminology

Return ONLY the refined translation, no explanations."""

        if glossary_terms:
            glossary_txt = "\n".join([f"{k} -> {v}" for k, v in glossary_terms.items()])
            system_prompt += f"\n\nMaintain these terms:\n{glossary_txt}"
        
        user_prompt = f"""Source text ({src_lang}):
{source_text}

Current translation ({tgt_lang}):
{translated_text}

Provide the improved translation:"""

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else translated_text
            
    def detect_chapters(self, text):
        """Structure AI - detect chapter boundaries in raw text."""
        if not self.client:
            import json
            return json.dumps([])
            
        system_prompt = "You are a professional editor. Identify the starting lines of all chapters in this text. Provide the chapter title and the exact first few words. Return only a JSON list."
        user_prompt = f"Text to analyze:\n{text[:8000]}\n\nJSON Output: [{{'title': '...', 'start_line': '...'}}]"

        is_translategemma = "translategemma" in self.model.lower()
        if is_translategemma:
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
