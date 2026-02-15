from src.engines.translation_engine import TranslationEngine
from openai import OpenAI
import os

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
        """
        Updates the model identifier for the LLM client.
        model_path is treated as the model name (e.g., 'gemma-3-12b')
        """
        self.model = model_path
        return True

    def translate(self, text, src_lang, tgt_lang, context=None, glossary_terms=None):
        if not self.client:
            return f"[LLM Config Missing] {text}"
            
        # Context building
        system_prompt = f"You are a professional novel translator. Translate the following text from {src_lang} to {tgt_lang}. Maintain the flow, tone, and style of a novel."
        
        if glossary_terms:
            glossary_txt = "\n".join([f"{k} -> {v}" for k, v in glossary_terms.items()])
            system_prompt += f"\n\nUse the following glossary terms strictly:\n{glossary_txt}"
            
        if context:
            user_prompt = f"Context:\n{context}\n\nText to translate:\n{text}"
        else:
            user_prompt = f"Text to translate:\n{text}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def generate_glossary(self, text, src_lang="Chinese", tgt_lang="French"):
        if not self.client:
            return "[]"

        system_prompt = f"You are a glossary extraction tool. Identify proper nouns (names, places, organizations, special terms) in the following {src_lang} text. Provide their likely {tgt_lang} translation based on context."
        user_prompt = f"Text:\n{text}\n\nOutput strict JSON format: [{{'source': 'term', 'target': 'translation', 'category': 'Name|Place|Item'}}]"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            # Clean markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                 content = content.split("```")[1].split("```")[0].strip()
            return content
        except Exception as e:
            print(f"Glossary Gen Error: {e}")
            return "[]"

    def translate_batch(self, texts, src_lang, tgt_lang):
        # Serial processing for now to avoid complexity with async/batch API
        return [self.translate(t, src_lang, tgt_lang) for t in texts]

    def get_supported_languages(self):
        return ["Any"]

    def get_name(self):
        return f"LLM ({self.model})"

    def is_available(self):
        return self.client is not None
