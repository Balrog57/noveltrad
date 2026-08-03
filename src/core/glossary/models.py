"""
Dataclasses for glossary entities.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

# Recognized gender values for a glossary entry. "unknown" is stored as None:
# it carries no information for the prompt, and keeping it out of the column
# means a NER pass that labels every location "unknown" does not fill the
# database with noise.
GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDER_UNKNOWN = "unknown"

#: Values that actually reach the prompt.
KNOWN_GENDERS = (GENDER_MALE, GENDER_FEMALE)

#: Values accepted on input (from the UI, an import file, or the NER pass).
ALLOWED_GENDERS = (GENDER_MALE, GENDER_FEMALE, GENDER_UNKNOWN)

#: Cap on the cast block. It is injected into every chunk, so an unbounded
#: list would be a permanent token tax on long sagas. 80 named characters
#: covers all but the largest ensembles at roughly 900 tokens.
DEFAULT_MAX_CAST_ENTRIES = 80


def normalize_gender(value) -> Optional[str]:
    """Coerce arbitrary input to 'male', 'female', or None.

    Accepts a few common spellings so hand-written CSV files and chatty LLM
    output both land on the canonical value: 'M'/'F', 'man'/'woman',
    'masculine'/'feminine'. Anything unrecognized — including 'unknown', the
    empty string, and None — yields None, which means "no gender information"
    everywhere downstream.
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in (GENDER_MALE, "m", "man", "boy", "masculine", "masc", "male."):
        return GENDER_MALE
    if text in (GENDER_FEMALE, "f", "woman", "girl", "feminine", "fem", "female."):
        return GENDER_FEMALE
    return None


@dataclass
class GlossaryTerm:
    """A single source -> target term entry."""
    source_term: str
    translated_term: str
    category: Optional[str] = None
    gender: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        self.gender = normalize_gender(self.gender)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source": self.source_term,
            "target": self.translated_term,
            "category": self.category or "",
            "gender": self.gender or "",
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GlossaryTerm":
        return cls(
            source_term=data.get("source") or data.get("source_term") or "",
            translated_term=data.get("target") or data.get("translated_term") or "",
            category=data.get("category") or None,
            gender=data.get("gender") or data.get("sex") or None,
            id=data.get("id"),
        )


@dataclass
class Glossary:
    """A named collection of terms for a specific source/target language pair."""
    name: str
    source_language: str = ""
    target_language: str = ""
    terms: List[GlossaryTerm] = field(default_factory=list)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def terms_dict(self) -> Dict[str, str]:
        """Returns {source_term: translated_term} mapping for filter."""
        return {t.source_term: t.translated_term for t in self.terms if t.source_term}

    @property
    def terms_metadata(self) -> Dict[str, Dict[str, str]]:
        """Returns {source_term: {category, gender}} for the injector.

        Only entries carrying at least one piece of metadata are included, so
        a glossary with no categories and no genders yields an empty dict and
        the injector can skip its optional sections entirely.
        """
        metadata: Dict[str, Dict[str, str]] = {}
        for t in self.terms:
            if not t.source_term:
                continue
            entry = {}
            if t.category:
                entry["category"] = t.category
            if t.gender:
                entry["gender"] = t.gender
            if entry:
                metadata[t.source_term] = entry
        return metadata

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_lang": self.source_language,
            "target_lang": self.target_language,
            "terms": [t.to_dict() for t in self.terms],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Glossary":
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            source_language=data.get("source_lang") or data.get("source_language") or "",
            target_language=data.get("target_lang") or data.get("target_language") or "",
            terms=[GlossaryTerm.from_dict(t) for t in (data.get("terms") or [])],
        )


@dataclass
class GlossaryConfig:
    """Behavior knobs for the per-chunk glossary filter."""
    max_entries: int = 50
    case_sensitive: bool = True
    warn_on_cap: bool = True
    max_cast_entries: int = DEFAULT_MAX_CAST_ENTRIES


@dataclass
class BulkReplaceResult:
    """Outcome of GlossaryStore.bulk_replace_terms.

    Reports how many rows were inserted and how many were skipped, so callers
    (especially the import endpoint) can explain to the user why N may be
    smaller than the number of rows in the source file.
    """
    inserted: int = 0
    skipped_empty: int = 0
    skipped_duplicate: int = 0
    total_input: int = 0

    def to_dict(self) -> Dict:
        return {
            "inserted": self.inserted,
            "skipped_empty": self.skipped_empty,
            "skipped_duplicate": self.skipped_duplicate,
            "total_input": self.total_input,
        }
