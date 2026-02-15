from peewee import Model, SqliteDatabase, CharField, TextField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
import datetime
import os

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
    status = CharField(default='untranslated') # untranslated, translated, validated
    metadata = TextField(null=True) # JSON string for format-specific data (node_index, etc.)
    
    class Meta:
        order_by = ('index',)

class GlossaryTerm(BaseModel):
    project = ForeignKeyField(Project, backref='glossary')
    source_term = CharField()
    target_term = CharField()
    category = CharField(default='general') # name, location, skill, etc.
    is_auto_generated = BooleanField(default=False)

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
    return db
