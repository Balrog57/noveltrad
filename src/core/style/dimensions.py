"""
Closed list of writing-style dimensions (Phase 3 of the style-extraction
plan, §2.4). Used by the extraction prompt, the parser's coercion step, and
the review UI's grouping.
"""

ALLOWED_DIMENSIONS: tuple = (
    "register",          # formality, distance, irony, emotional temperature
    "narrative_voice",   # person, tense, focalization, narrator presence
    "sentence_rhythm",   # length distribution, parataxis vs subordination, cadence
    "lexicon",           # concrete vs abstract, recurring lexical fields, archaisms
    "imagery",           # metaphors, similes, recurring figurative motifs
    "dialogue",          # speech tags, orality, idiolects, interruption handling
    "punctuation",       # em-dashes, semicolons, ellipses, exclamation frequency
    "formatting",        # paragraph length, italics usage, section breaks
    "other",
)

DEFAULT_DIMENSION = "other"
