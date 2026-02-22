"""
Glossary Applier - Application automatique du glossaire

Applique le glossaire après traduction NMT (NLLB, Argos) pour
assurer la cohérence terminologique.
"""

import re
from typing import List, Dict, Optional


class GlossaryApplier:
    """
    Applique automatiquement le glossaire après traduction.
    
    Usage:
        applier = GlossaryApplier(glossary)
        result = applier.apply(translated_text)
    """
    
    def __init__(self, glossary):
        """
        Args:
            glossary: Liste de {source, target, variants?} ou Dictionnaire {source: target}
        """
        if isinstance(glossary, dict):
            self.glossary = [{"source": k, "target": v} for k, v in glossary.items()]
        else:
            self.glossary = glossary or []
        
        # Trier par longueur (plus long d'abord) pour éviter les remplacements partiels
        # Trier par longueur (plus long d'abord) pour éviter les remplacements partiels
        self.glossary_sorted = sorted(
            glossary, 
            key=lambda x: len(x.get("source", "")), 
            reverse=True
        )
        
    def apply(
        self, 
        text: str, 
        case_sensitive: bool = False,
        whole_word: bool = True
    ) -> str:
        """
        Applique le glossaire sur le texte traduit.
        
        Args:
            text: Texte traduit où appliquer le glossaire
            case_sensitive: Respecter la casse
            whole_word: Matcher mots entiers seulement
            
        Returns:
            Texte avec le glossaire appliqué
        """
        result = text
        
        for entry in self.glossary_sorted:
            source = entry.get("source", "")
            target = entry.get("target", "")
            
            if not source or not target:
                continue
                
            # Construire le pattern regex
            if whole_word:
                # Ajouter boundaries de mot
                pattern = r'\b' + re.escape(source) + r'\b'
            else:
                pattern = re.escape(source)
                
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # Remplacer
            result = re.sub(pattern, target, result, flags=flags)
            
        return result
    
    def apply_batch(
        self, 
        texts: List[str],
        **kwargs
    ) -> List[str]:
        """Applique le glossaire sur une liste de textes."""
        return [self.apply(text, **kwargs) for text in texts]
    
    def highlight_terms(
        self, 
        text: str, 
        marker: str = "**"
    ) -> str:
        """
        Met en évidence les termes du glossaire dans le texte.
        
        Args:
            text: Texte à analyser
            marker: Marqueur de surbrillance (** pour markdown)
            
        Returns:
            Texte avec les termes marqués
        """
        result = text
        
        for entry in self.glossary_sorted:
            source = entry.get("source", "")
            if not source:
                continue
                
            pattern = r'\b' + re.escape(source) + r'\b'
            result = re.sub(
                pattern, 
                f"{marker}{source}{marker}", 
                result, 
                flags=re.IGNORECASE
            )
            
        return result


class GlossaryMatcher:
    """
    Trouve les termes du glossaire présents dans un texte.
    
    Usage:
        matcher = GlossaryMatcher(glossary)
        found = matcher.find_in(text)
    """
    
    def __init__(self, glossary):
        if isinstance(glossary, dict):
            self.glossary = [{"source": k, "target": v} for k, v in glossary.items()]
        else:
            self.glossary = glossary or []
        
    def find_in(
        self, 
        text: str,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        Trouve tous les termes du glossaire dans le texte.
        
        Returns:
            Liste de {entry, position, match}
        """
        found = []
        
        for entry in self.glossary:
            source = entry.get("source", "")
            if not source:
                continue
                
            pattern = r'\b' + re.escape(source) + r'\b'
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for match in re.finditer(pattern, text, flags=flags):
                found.append({
                    "entry": entry,
                    "position": match.start(),
                    "match": match.group()
                })
                
        # Trier par position
        return sorted(found, key=lambda x: x["position"])


# Application automatique pendant traduction NMT
class NMTGlossaryPipeline:
    """
    Pipeline: Traduction NMT → Application Glossaire
    
    Usage:
        pipeline = NMTGlossaryPipeline(nmt_engine, glossary)
        result = pipeline.translate(text)
    """
    
    def __init__(self, nmt_engine, glossary):
        self.nmt_engine = nmt_engine
        self.applier = GlossaryApplier(glossary)
        
    async def translate(
        self, 
        text: str,
        src_lang: str = "en",
        tgt_lang: str = "fr"
    ) -> str:
        """
        Traduit puis applique le glossaire.
        """
        # 1. Traduction NMT
        translated = await self.nmt_engine.translate(
            text, src_lang, tgt_lang
        )
        
        # 2. Application glossaire
        result = self.applier.apply(translated)
        
        return result


# Exemple d'utilisation
"""
# Dans le flux de traduction:
from src.engines.nllb_engine import NLLBEngine
from src.core.glossary_applier import NMTGlossaryPipeline

# Charger le glossaire
glossary = [
    {"source": "Zhang Xuan", "target": "Zhang Xuan"},
    {"source": "Spirit Pawn", "target": "Pion d'Esprit"},
]

# Créer le pipeline
nmt = NLLBEngine()
pipeline = NMTGlossaryPipeline(nmt, glossary)

# Traduire avec application automatique du glossaire
result = await pipeline.translate("Zhang Xuan cultivait le Spirit Pawn.")
print(result)  # Zhang Xuan cultivait le Pion d'Esprit.
"""
