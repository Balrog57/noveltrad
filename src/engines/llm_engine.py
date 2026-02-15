from src.engines.translation_engine import TranslationEngine
from openai import OpenAI
from typing import List
import json

GENRE_PROMPTS = {
    "xianxia": """You are an expert in Chinese fantasy novels (Xianxia). Identify:
- Cultivation realms and levels
- Cultivation techniques and methods
- Magical items and weapons
- Sects and organizations
- Proper names (characters, places)
- Cultural terms and concepts""",
    
    "scifi": """You are an expert in Science Fiction. Identify:
- Technology terms and devices
- Spaceships and vehicles
- Planets and locations
- Alien species and factions
- Scientific concepts
- Proper names (characters, ships, planets)""",
    
    "fantasy": """You are an expert in Fantasy literature. Identify:
- Magical creatures and beings
- Spells and enchantments
- Locations and realms
- Artifacts and magical items
- Factions and organizations
- Proper names (characters, places)""",
    
    "romance": """You are an expert in Romance novels. Identify:
- Character names
- Relationship titles
- Emotional concepts
- Setting locations
- Character traits""",
    
    "general": """You are a glossary extraction tool. Identify:
- Proper names (characters, places)
- Organizations
- Key terms and concepts
- Cultural or domain-specific vocabulary"""
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

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        if not self.client:
            return f"[LLM Config Missing] {text}"
            
        system_prompt = f"You are a professional novel translator. Translate from {src_lang} to {tgt_lang}. Maintain novel flow and tone."
        
        if glossary_terms:
            glossary_txt = "\n".join([f"{k} -> {v}" for k, v in glossary_terms.items()])
            system_prompt += f"\n\nUse these terms strictly:\n{glossary_txt}"
            
        if context:
            user_prompt = f"Context:\n{context}\n\nTranslate:\n{text}"
        else:
            user_prompt = f"Translate:\n{text}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def generate_glossary(self, text, src_lang="Chinese", tgt_lang="French", genre="general"):
        """Generate glossary terms from text using LLM."""
        if not self.client:
            return json.dumps([])

        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        
        system_prompt = f"""{genre_prompt}
Extract important terms needing consistent translation.
Return JSON array with: source, target, category."""
        
        user_prompt = f"""Source: {src_lang} -> Target: {tgt_lang}

Text:
{text[:3000]}

JSON array like:
[{{"source": "term", "target": "translation", "category": "Name"}}]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            if not content:
                return json.dumps([])
                
            content = content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            terms = json.loads(content)
            return json.dumps(terms, ensure_ascii=False)
            
        except json.JSONDecodeError:
            return json.dumps([])
        except Exception as e:
            print(f"Glossary Gen Error: {e}")
            return json.dumps([])

    def generate_glossary_incremental(self, text, existing_terms, src_lang="Chinese", tgt_lang="French", genre="general"):
        """Generate glossary incrementally, avoiding duplicates."""
        if not self.client:
            return json.dumps([])
            
        existing_list = existing_terms[:50] if isinstance(existing_terms, list) else []
        existing_str = "\n".join([f"- {e.get('source', e.get('source_term', ''))} -> {e.get('target', e.get('target_term', ''))}" for e in existing_list])
        
        genre_prompt = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["general"])
        
        system_prompt = f"""{genre_prompt}
Extract NEW terms NOT in existing glossary.
Existing:
{existing_str}

Return ONLY new terms as JSON array."""
        
        user_prompt = f"""Source: {src_lang} -> Target: {tgt_lang}

New text:
{text[:3000]}

JSON:
[{{"source": "term", "target": "translation", "category": "Name"}}]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            if not content:
                return json.dumps([])
                
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return content
            
        except Exception as e:
            print(f"Incremental Glossary Error: {e}")
            return json.dumps([])

    def translate_batch(self, texts, src_lang, tgt_lang):
        return [self.translate(t, src_lang, tgt_lang) for t in texts]

    def get_supported_languages(self):
        return ["Any"]

    def get_name(self):
        return f"LLM ({self.model})"

    def is_available(self):
        return self.client is not None
