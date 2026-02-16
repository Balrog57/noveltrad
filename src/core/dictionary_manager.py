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

    def has_language(self, code):
        """Checks if there are any terms with this source code."""
        return GlobalDictionaryTerm.select().where(GlobalDictionaryTerm.source_lang == code).exists()
        
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
        
    def download_dictionary(self, language_code, callback=None):
        """
        Attempts to download a dictionary for the given language code.
        Defaults to Kaikki.org (Language -> English definitions).
        """
        # specialized handling for Chinese -> French (CFDICT)
        if language_code == 'zh':
             return self._download_cfdict(callback)
             
        # generic handling: Kaikki (Language -> English)
        return self._download_kaikki(language_code, callback)

    def _download_cfdict(self, callback):
        """Downloads CFDICT (Chinese -> French)."""
        url = "https://raw.githubusercontent.com/settlen/cfdict/master/cfdict.u8"
        try:
            if callback: callback("Downloading CFDICT...", 10)
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            temp_path = os.path.join(os.path.dirname(self.db_path), "cfdict.temp")
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            if callback: callback("Importing CFDICT...", 50)
            
            # Import (Format: Traditional Simplified [pinyin] /Meanings/)
            count = 0
            with open(temp_path, 'r', encoding='utf-8') as f:
                with db.atomic():
                    for line in f:
                        if line.startswith('#'): continue
                        # Parse CFDICT line
                        # This is a rough parser, CFDICT format is specific
                        # Trad Simp [pinyin] /English/French/
                        parts = line.split(' ')
                        if len(parts) > 2:
                            # Simply take the whole line for now or improve parsing
                            # Better: use a library/regex
                            # For now, we store raw line as "context" or simplistic parsing
                            # source = Simplified (parts[1])
                            # target = Meanings (after /)
                            simp = parts[1]
                            rest = " ".join(parts[2:])
                            if '/' in rest:
                                _, meanings = rest.split('/', 1)
                                meanings = meanings.strip('/')
                                self.add_term('zh', 'fr', simp, meanings)
                                count += 1
                                
            os.remove(temp_path)
            if callback: callback(f"Installed {count} terms.", 100)
            return True
            
        except Exception as e:
            print(f"CFDICT download failed: {e}")
            return False

    def _download_kaikki(self, code, callback):
        """Downloads from Kaikki.org (Language -> English)."""
        from src.engines.llm_engine import LANGUAGE_NAMES
        
        name = LANGUAGE_NAMES.get(code)
        if not name:
            name = LANGUAGE_NAMES.get(code.split('_')[0]) # Try generic code
            
        # Kaikki uses full English names, Title Case (e.g. 'French', 'Japanese')
        if not name:
            print(f"Could not find name for code {code}")
            return False
            
        # Ensure capitalization
        name = name.title()
        
        url = f"https://kaikki.org/dictionary/{name}/words.jsonl.gz"
        
        try:
            if callback: callback(f"Downloading {name} dictionary...", 10)
            response = requests.get(url, stream=True)
            if response.status_code == 404:
                # Try finding mapped name (sometimes specific handling needed)
                print(f"Dictionary not found for {name} at {url}")
                return False
                
            response.raise_for_status()
            
            # Save .gz
            gz_path = os.path.join(os.path.dirname(self.db_path), f"{code}_dict.jsonl.gz")
            with open(gz_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if callback: callback(f"Extracting {name} dictionary...", 40)
            
            # Extract and Import
            import gzip
            count = 0
            
            # We process line by line to avoid memory issues
            with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
                with db.atomic(): # Transaction might be too large for whole file?
                    # Batch commit every 1000
                    batch_size = 1000
                    batch = []
                    
                    for line in f:
                        try:
                            entry = json.loads(line)
                            word = entry.get('word')
                            senses = entry.get('senses', [])
                            
                            if not word or not senses: continue
                            
                            # Get first gloss
                            gloss = None
                            for sense in senses:
                                if 'glosses' in sense:
                                    gloss = "; ".join(sense['glosses'])
                                    break
                            
                            if gloss:
                                batch.append(('zh' if code == 'zh' else code, 'en', word, gloss, None))
                                
                            if len(batch) >= batch_size:
                                self.bulk_add_safe(batch)
                                count += len(batch)
                                batch = []
                                if callback and count % 5000 == 0:
                                    callback(f"Imported {count} terms...", 50)
                                    
                        except Exception:
                            continue
                    
                    if batch:
                        self.bulk_add_safe(batch)
                        count += len(batch)
                        
            os.remove(gz_path)
            if callback: callback(f"Installed {count} terms.", 100)
            return True
            
        except Exception as e:
            print(f"Kaikki download failed: {e}")
            return False

    def bulk_add_safe(self, terms_list):
        """Bulk add with conflict handling."""
        # SQLite bulk insert
        # We use a custom query since peewee's bulk_create might not handleignore
        data = [{'source_lang': i[0], 'target_lang': i[1], 'source_term': i[2], 'target_term': i[3], 'context': i[4]} for i in terms_list]
        try:
             # Insert many
             with db.atomic():
                 GlobalDictionaryTerm.insert_many(data).on_conflict_ignore().execute()
        except:
             pass
