"""
Which target languages need the glossary block's target-side inflection line.

The glossary lists one citation form per term while telling the model to use
"these EXACT translations". For a language with grammatical case that is a
contradiction, so the block emits an extra instruction — but only for the
languages where the contradiction is real.
"""
from src.utils.lang_normalize import normalize_lang_key

# Inclusion criterion: case/number inflection of nouns and adjectives changes
# the WRITTEN form of the term itself, so a glossary term's citation form is
# routinely not the form that appears in a running sentence.
#
# Deliberate exclusions, on that same criterion:
# - Chinese, Japanese, Korean, Vietnamese, Thai, Indonesian: no stem-modifying
#   case morphology; particles attach without altering the term.
# - English, French, Spanish, Italian, Portuguese, Dutch: no productive
#   nominal case system.
# - Bulgarian, Macedonian: Slavic but they lost nominal case declension.
# - Arabic: richly inflected, but its case endings are unwritten diacritics,
#   so they do not change the rendered string.
INFLECTED_TARGET_LANGUAGES: frozenset = frozenset({
    "russian",
    "ukrainian",
    "belarusian",
    "polish",
    "czech",
    "slovak",
    "slovenian",
    "croatian",
    "serbian",
    "bosnian",
    "german",
    "greek",
    "latvian",
    "lithuanian",
    "estonian",
    "finnish",
    "hungarian",
    "turkish",
    "romanian",
    "icelandic",
    "georgian",
    "armenian",
    "hindi",
    "latin",
})


def target_language_is_inflected(target_language: str) -> bool:
    """True when case/number inflection changes the written form of a noun in the
    target language, so a glossary term's citation form is routinely not the form
    that appears in a running sentence."""
    if not target_language:
        return False
    return normalize_lang_key(target_language) in INFLECTED_TARGET_LANGUAGES
