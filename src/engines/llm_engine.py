from src.engines.translation_engine import TranslationEngine
from openai import OpenAI
import os

class LLMEngine(TranslationEngine):
    def __init__(self, api_key=None, base_url=None, model="gpt-3.5-turbo"):
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

    def translate(self, text, src_lang, tgt_lang, context=None):
        if not self.client:
            return f"[LLM Config Missing] {text}"
            
        # Context building
        system_prompt = f"You are a professional novel translator. Translate the following text from {src_lang} to {tgt_lang}. Maintain the flow, tone, and style of a novel."
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

    def translate_batch(self, texts, src_lang, tgt_lang):
        # Serial processing for now to avoid complexity with async/batch API
        return [self.translate(t, src_lang, tgt_lang) for t in texts]

    def get_supported_languages(self):
        return ["Any"]

    def get_name(self):
        return f"LLM ({self.model})"

    def is_available(self):
        return self.client is not None
