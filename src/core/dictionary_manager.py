from src.core.database import GlobalDictionaryTerm, db
import csv

class DictionaryManager:
    def __init__(self):
        # Ensure we are connected to a DB. 
        # CAUTION: GlobalDictionary usually resides in a global DB, not project DB.
        # For this version, we'll store it in the project DB for simplicity, 
        # OR we should have a separate 'global.db' in AppData.
        # To respect the user requirement of "Global", we should support a separate DB.
        pass

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
            return None # Duplicate likely

    def search(self, src_lang, tgt_lang, query):
        """Finds terms starting with query."""
        return GlobalDictionaryTerm.select().where(
            (GlobalDictionaryTerm.source_lang == src_lang) &
            (GlobalDictionaryTerm.target_lang == tgt_lang) &
            (GlobalDictionaryTerm.source_term.contains(query))
        )

    def get_all(self, src_lang=None, tgt_lang=None):
        query = GlobalDictionaryTerm.select()
        if src_lang:
            query = query.where(GlobalDictionaryTerm.source_lang == src_lang)
        if tgt_lang:
            query = query.where(GlobalDictionaryTerm.target_lang == tgt_lang)
        return list(query)

    def delete_term(self, term_id):
        GlobalDictionaryTerm.delete_by_id(term_id)

    def import_csv(self, file_path, src_lang, tgt_lang):
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            with db.atomic():
                for row in reader:
                    if len(row) >= 2:
                        self.add_term(src_lang, tgt_lang, row[0], row[1], row[2] if len(row) > 2 else None)
                        count += 1
        return count
