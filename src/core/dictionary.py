import sqlite3
import json
import os

class DictionaryManager:
    def __init__(self, db_path="data/dictionary.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                reading TEXT,
                definitions TEXT, -- JSON list of strings
                lang TEXT DEFAULT 'zh'
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_word ON dictionary(word)')
        conn.commit()
        conn.close()

    def search(self, query):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Exact match first, then partial
        c.execute("SELECT word, reading, definitions, lang FROM dictionary WHERE word = ?", (query,))
        exact_results = c.fetchall()
        
        results = []
        for r in exact_results:
            results.append({
                "word": r[0],
                "reading": r[1],
                "definitions": json.loads(r[2]),
                "lang": r[3],
                "match": "exact"
            })
            
        # If no exact match, try like
        if not results:
             c.execute("SELECT word, reading, definitions, lang FROM dictionary WHERE word LIKE ? LIMIT 5", (f"{query}%",))
             partial_results = c.fetchall()
             for r in partial_results:
                results.append({
                    "word": r[0],
                    "reading": r[1],
                    "definitions": json.loads(r[2]),
                    "lang": r[3], 
                    "match": "partial"
                })

        conn.close()
        return results

    def add_entry(self, word, reading, definitions, lang='zh'):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO dictionary (word, reading, definitions, lang) VALUES (?, ?, ?, ?)",
                  (word, reading, json.dumps(definitions), lang))
        conn.commit()
        conn.close()
