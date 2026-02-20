"""
Glossary AI - Génération automatique de glossaire via LLM

Ce module utilise un LLM pour analyser un texte source et générer
automatiquement un glossaire des termes importants (noms de personnages,
lieux, concepts spécifiques au genre, etc.)
"""

from typing import List, Dict, Optional
import json
import re


class GlossaryAI:
    """
    Génère un glossaire automatiquement via LLM.
    
    Usage:
        glossary_ai = GlossaryAI(llm_engine)
        terms = glossary_ai.generate(text, genre="xianxia")
    """
    
    # Prompts par genre
    PROMPTS = {
        "xianxia": """Tu es un expert en novels xianxia (cultivation, arts martiaux chinois).
Analyse le texte suivant etextrait un glossaire des termes importants.

Termes à extraire:
- Noms de personnages (et surnoms/titres)
- Techniques de cultivation (formations, artes martiales)
- Rang/grades (immortel, démon, etc.)
- Objets magiques, ingrédients
- Lieux (montagnes, sects, royaumes)
- Organisations (sects, clans)

Réponds en JSON:
[{"term": "terme source", "translation": "traduction", "category": "categorie", "context": "contexte"}]""",
        
        "scifi": """Tu es un expert en science-fiction.
Analyse le texte suivant etextrait un glossaire des termes importants.

Termes à extraire:
- Noms de personnages
- Technologies fictives
- Vaisseaux, stations, planètes
- Races extraterrestres
- Concepts scientifiques

Réponds en JSON:
[{"term": "terme source", "translation": "traduction", "category": "categorie", "context": "contexte"}]""",
        
        "fantasy": """Tu es un expert en fantasy.
Analyse le texte suivant etextrait un glossaire des termes importants.

Termes à extraire:
- Noms de personnages
- Creatures magiques
- Lieux enchantés
- Objets légendaires
- Magie/sorts
- Organisations (guilde, ordre)

Réponds en JSON:
[{"term": "terme source", "translation": "traduction", "category": "categorie", "context": "contexte"}]""",
        
        "general": """Analyse le texte suivant etextrait un glossaire des termes importants.

Termes à extraire:
- Noms de personnages
- Lieux
- Termes techniques ou spécifiques

Réponds en JSON:
[{"term": "terme source", "translation": "traduction", "category": "categorie", "context": "contexte"}]"""
    }
    
    def __init__(self, llm_engine):
        """
        Args:
            llm_engine: Instance de LLMEngine (OpenAI, LM Studio, Ollama)
        """
        self.llm = llm_engine
        
    def generate(
        self, 
        text: str, 
        genre: str = "general",
        max_terms: int = 50
    ) -> List[Dict]:
        """
        Génère un glossaire à partir d'un texte.
        
        Args:
            text: Texte source à analyser
            genre: Genre du novel (xianxia, scifi, fantasy, general)
            max_terms: Nombre maximum de termes à extraire
            
        Returns:
            Liste de dictionnaires avec {term, translation, category, context}
        """
        prompt = self._build_prompt(text, genre)
        
        try:
            response = self.llm.chat(prompt)
            terms = self._parse_response(response)
            
            # Limiter le nombre de termes
            return terms[:max_terms]
            
        except Exception as e:
            print(f"Erreur GlossaryAI: {e}")
            return []
    
    def _build_prompt(self, text: str, genre: str) -> str:
        """Construit le prompt selon le genre."""
        base_prompt = self.PROMPTS.get(genre, self.PROMPTS["general"])
        
        # Limiter la taille du texte (contexte LLM)
        # Prendre les premiers ~2000 caractères
        text_sample = text[:2000]
        
        return f"""{base_prompt}

Texte à analyser:
{text_sample}

Réponds uniquement en JSON valide, sans autre texte."""
    
    def _parse_response(self, response: str) -> List[Dict]:
        """Parse la réponse JSON du LLM."""
        try:
            # Extraire le JSON de la réponse
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return self._normalize_terms(data)
            return []
        except json.JSONDecodeError:
            print("Erreur: réponse JSON invalide")
            return []
    
    def _normalize_terms(self, data: List) -> List[Dict]:
        """Normalise les termes extraits."""
        normalized = []
        for item in data:
            normalized.append({
                "term": item.get("term", item.get("source", "")),
                "translation": item.get("translation", item.get("target", "")),
                "category": item.get("category", "general"),
                "context": item.get("context", ""),
                "source": "ai_generated"
            })
        return normalized


# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple avec un mock LLM
    class MockLLM:
        def chat(self, prompt):
            return '''[
                {"term": "Zhang Xuan", "translation": "Zhang Xuan", "category": "personnage", "context": "Protagoniste du novel"},
                {"term": "Spirit Pawn", "translation": "Pion d'Esprit", "category": "rang", "context": "Premier rang de cultivation"}
            ]'''
    
    llm = MockLLM()
    glossary_ai = GlossaryAI(llm)
    
    sample_text = "Zhang Xuan cultivait le Spirit Pawn. Il entra dans la chambre de cultivation..."
    terms = glossary_ai.generate(sample_text, genre="xianxia")
    
    for term in terms:
        print(f"{term['term']} -> {term['translation']} ({term['category']})")
