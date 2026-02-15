from src.core.database import GlobalDictionaryTerm, db
import csv
import os
import json

SUPPORTED_LANGUAGES = {
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'th': 'Thai',
    'vi': 'Vietnamese',
}

class DictionaryManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or self._get_default_db_path()
        self._ensure_db_exists()
        
    def _get_default_db_path(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data", "dictionaries")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "dictionary.db")
        
    def _ensure_db_exists(self):
        if not os.path.exists(self.db_path):
            db.init(self.db_path)
            db.connect()
            db.create_tables([GlobalDictionaryTerm])
        elif not db.is_connection_usable():
            db.init(self.db_path)
            db.connect()
            
    def add_term(self, src_lang, tgt_lang, source, target, context=None):
        try:
            return GlobalDictionaryTerm.create(
                source_lang=src_lang,
                target_lang=tgt_lang,
                source_term=source,
                target_term=target,
                context=context
            )
        except Exception:
            return None
            
    def search(self, src_lang, tgt_lang, query, limit=20):
        """Finds terms containing query in source or target."""
        if not query:
            return []
            
        query_lower = query.lower()
        
        results = GlobalDictionaryTerm.select().where(
            (GlobalDictionaryTerm.source_lang == src_lang) &
            (GlobalDictionaryTerm.target_lang == tgt_lang) &
            (GlobalDictionaryTerm.source_term.contains(query))
        ).limit(limit)
        
        return list(results)
        
    def search_bidirectional(self, query, src_lang=None, tgt_lang=None, limit=20):
        """Search in both directions for any language pair."""
        if not query:
            return []
            
        conditions = (
            (GlobalDictionaryTerm.source_term.contains(query)) |
            (GlobalDictionaryTerm.target_term.contains(query))
        )
        
        if src_lang:
            conditions = conditions & (GlobalDictionaryTerm.source_lang == src_lang)
        if tgt_lang:
            conditions = conditions & (GlobalDictionaryTerm.target_lang == tgt_lang)
            
        return list(GlobalDictionaryTerm.select().where(conditions).limit(limit))
        
    def get_all(self, src_lang=None, tgt_lang=None):
        query = GlobalDictionaryTerm.select()
        if src_lang:
            query = query.where(GlobalDictionaryTerm.source_lang == src_lang)
        if tgt_lang:
            query = query.where(GlobalDictionaryTerm.target_lang == tgt_lang)
        return list(query)
        
    def delete_term(self, term_id):
        GlobalDictionaryTerm.delete_by_id(term_id)
        
    def get_languages(self):
        """Get list of available language pairs in dictionary."""
        pairs = set()
        for term in GlobalDictionaryTerm.select(GlobalDictionaryTerm.source_lang, GlobalDictionaryTerm.target_lang).distinct():
            pairs.add((term.source_lang, term.target_lang))
        return list(pairs)
        
    def import_csv(self, file_path, src_lang, tgt_lang):
        """Import CSV with format: source,target[,context]"""
        count = 0
        errors = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                with db.atomic():
                    for row in reader:
                        if len(row) >= 2:
                            try:
                                self.add_term(src_lang, tgt_lang, row[0].strip(), row[1].strip(), row[2].strip() if len(row) > 2 else None)
                                count += 1
                            except Exception:
                                errors += 1
        except Exception as e:
            return 0, str(e)
            
        return count, errors
        
    def import_stardict(self, dir_path):
        """Import StarDict format dictionaries (.ifo, .idx, .dict)"""
        # Simplified implementation - just scan for .txt/.csv files
        count = 0
        for fname in os.listdir(dir_path):
            if fname.endswith('.csv'):
                # Try to detect language from filename
                parts = fname.replace('.csv', '').split('_')
                if len(parts) >= 2:
                    src_lang = parts[0]
                    tgt_lang = parts[1]
                    c, e = self.import_csv(os.path.join(dir_path, fname), src_lang, tgt_lang)
                    count += c
        return count
        
    def export_csv(self, file_path, src_lang=None, tgt_lang=None):
        """Export dictionary to CSV"""
        terms = self.get_all(src_lang, tgt_lang)
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target', 'context'])
            for term in terms:
                writer.writerow([term.source_term, term.target_term, term.context or ''])
                
        return len(terms)
        
    def get_stats(self):
        """Get dictionary statistics"""
        total = GlobalDictionaryTerm.select().count()
        pairs = self.get_languages()
        
        stats = {
            'total_terms': total,
            'language_pairs': len(pairs),
            'pairs': pairs
        }
        
        return stats
        
    def bulk_add(self, terms_list):
        """Bulk add list of terms [(src_lang, tgt_lang, source, target, context), ...]"""
        count = 0
        with db.atomic():
            for item in terms_list:
                try:
                    GlobalDictionaryTerm.create(
                        source_lang=item[0],
                        target_lang=item[1],
                        source_term=item[2],
                        target_term=item[3],
                        context=item[4] if len(item) > 4 else None
                    )
                    count += 1
                except Exception:
                    pass
        return count
