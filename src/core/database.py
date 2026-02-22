from peewee import Model, SqliteDatabase, CharField, TextField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
import datetime
import os
from src.core.segment_status import SegmentStatus

db = SqliteDatabase(None)  # Placeholder, will be initialized at runtime

class BaseModel(Model):
    class Meta:
        database = db

class Project(BaseModel):
    name = CharField()
    source_language = CharField(default='en')
    target_language = CharField(default='fr')
    genre = CharField(default='general')  # xianxia, scifi, fantasy, romance, general
    custom_instructions = TextField(null=True)  # Custom translation instructions
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    file_path = CharField(null=True) # Path to the original file

class Chapter(BaseModel):
    project = ForeignKeyField(Project, backref='chapters')
    title = CharField()
    order_index = IntegerField()
    status = CharField(default='pending') # pending, in_progress, translated, reviewed

    class Meta:
        order_by = ('order_index',)

class Segment(BaseModel):
    project = ForeignKeyField(Project, backref='all_segments') # Keep global project link for easy queries
    chapter = ForeignKeyField(Chapter, backref='segments', null=True) # Allow null for transition/orphan segments
    index = IntegerField()
    source_text = TextField()
    target_text = TextField(null=True)
    status = CharField(default=SegmentStatus.UNTRANSLATED.value) 
    metadata = TextField(null=True) # JSON string for format-specific data (node_index, etc.)
    
    def set_status(self, new_status: SegmentStatus):
        self.status = new_status.value
        self.save()
        
    def get_status(self) -> SegmentStatus:
        return SegmentStatus.from_string(self.status)
    
    class Meta:
        order_by = ('index',)

class GlossaryTerm(BaseModel):
    project = ForeignKeyField(Project, backref='glossary')
    source_term = CharField()
    target_term = CharField()
    category = CharField(default='general') # name, location, skill, etc.
    is_auto_generated = BooleanField(default=False)
    
    # Phase C: Enriched Glossary
    variants = TextField(null=True) # JSON list of strings
    priority = IntegerField(default=10) # Higher number = higher priority
    notes = TextField(null=True)
    case_sensitive = BooleanField(default=True)
    source = CharField(default='manual') # manual, ai_generated, validated
    feedback_history = TextField(null=True) # JSON list of feedback/corrections
    created_at = DateTimeField(default=datetime.datetime.now)

class GlobalDictionaryTerm(BaseModel):
    source_lang = CharField() # e.g., 'en', 'zh', 'de'
    target_lang = CharField() # e.g., 'fr', 'en'
    source_term = CharField()
    target_term = CharField()
    context = TextField(null=True) # Optional context or notes
    
    class Meta:
        indexes = (
            # Unique index to prevent duplicates for the same pair/languages
            (('source_lang', 'target_lang', 'source_term'), True),
        )

class TranslationMemory(BaseModel):
    source_lang = CharField()
    target_lang = CharField()
    source_text = TextField()
    target_text = TextField()
    project = ForeignKeyField(Project, backref='translation_memory', null=True)
    tmx_id = CharField(null=True)  # UUID for TMX export
    metadata = TextField(null=True)  # JSON metadata (chapter, genre, engine, etc.)
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        indexes = (
            (('source_lang', 'target_lang', 'source_text'), False),
        )

def init_db(db_path):
    db.init(db_path)
    db.connect()
    # Create tables separately to handle references
    db.create_tables([Project, Chapter, Segment, GlossaryTerm, GlobalDictionaryTerm, TranslationMemory])
    
    # Phase C: Auto-migration for existing databases
    # Silence errors if columns already exist
    migrations = [
        ('glossaryterm', 'variants', 'TEXT'),
        ('glossaryterm', 'priority', 'INTEGER DEFAULT 10'),
        ('glossaryterm', 'notes', 'TEXT'),
        ('glossaryterm', 'case_sensitive', 'INTEGER DEFAULT 1'),
        ('glossaryterm', 'source', "VARCHAR(255) DEFAULT 'manual'"),
        ('glossaryterm', 'feedback_history', 'TEXT'),
        ('glossaryterm', 'created_at', 'DATETIME'),
        ('translationmemory', 'tmx_id', 'VARCHAR(255)'),
        ('translationmemory', 'metadata', 'TEXT')
    ]
    
    for table, col, type_def in migrations:
        try:
            db.execute_sql(f'ALTER TABLE {table} ADD COLUMN {col} {type_def}')
        except:
            pass
            
    return db
