import json
from typing import List, Dict, Optional
from peewee import IntegrityError
from src.core.database import GlobalDictionaryTerm

class DictionaryManager:
    """Manages local dictionary operations (search, add, import)."""
    
    @staticmethod
    def search_term(term: str, src_lang: Optional[str] = None, tgt_lang: Optional[str] = None) -> List[Dict]:
        """
        Search for a term in the local dictionary.
        Supports partial matches.
        """
        if not term:
            return []
            
        from src.core.database import db
        if not db or db.database is None:
            return []
            
        query = GlobalDictionaryTerm.select().where(
            (GlobalDictionaryTerm.source_term.contains(term)) | 
            (GlobalDictionaryTerm.target_term.contains(term))
        )
        
        if src_lang:
            query = query.where(GlobalDictionaryTerm.source_lang == src_lang)
        if tgt_lang:
            query = query.where(GlobalDictionaryTerm.target_lang == tgt_lang)
            
        # Limit results to avoid hanging on very common substrings
        query = query.limit(100)
        
        results = []
        for match in query:
            results.append({
                'source_term': match.source_term,
                'target_term': match.target_term,
                'source_lang': match.source_lang,
                'target_lang': match.target_lang,
                'context': match.context
            })
            
        return results

    @staticmethod
    def has_language(lang_code: str) -> bool:
        """
        Check if the local dictionary has any entries for a given language code.
        """
        from src.core.database import db
        if not db or db.database is None:
            return False
            
        try:
            return GlobalDictionaryTerm.select().where(
                (GlobalDictionaryTerm.source_lang == lang_code) | 
                (GlobalDictionaryTerm.target_lang == lang_code)
            ).exists()
        except Exception as e:
            # Silent failure for has_language if DB is busy/uninitialized
            return False

    @staticmethod
    def add_term(source_term: str, target_term: str, src_lang: str = 'auto', tgt_lang: str = 'auto', context: str = None) -> bool:
        """
        Add a new term to the local dictionary.
        Returns True if added, False if it already exists or failed.
        """
        if not source_term or not target_term:
            return False
            
        try:
            GlobalDictionaryTerm.create(
                source_lang=src_lang,
                target_lang=tgt_lang,
                source_term=source_term.strip(),
                target_term=target_term.strip(),
                context=context.strip() if context else None
            )
            return True
        except IntegrityError:
            # Term pair already exists due to unique index constraints
            return False
        except Exception as e:
            print(f"Error adding dictionary term: {e}")
            return False

    @staticmethod
    def import_from_json(filepath: str, src_lang: str, tgt_lang: str) -> int:
        """
        Import dictionary terms from a JSON file.
        Expected format: {"source_word": "target_definition_or_translation", ...}
        Returns the number of successfully imported terms.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            count = 0
            # Use chunks for faster bulk inserts if needed, but loop is safer for catching IntegrityError
            for src, tgt in data.items():
                # Handling lists or strings for target
                target_str = ", ".join(tgt) if isinstance(tgt, list) else str(tgt)
                if DictionaryManager.add_term(src, target_str, src_lang, tgt_lang):
                    count += 1
            return count
        except Exception as e:
            print(f"Failed to import dictionary JSON: {e}")
            return 0
