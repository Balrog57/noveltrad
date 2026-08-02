"""
Language name normalization for dict lookups.

The UI may pass regional variants like "Portuguese (Brazil)" or
"Portuguese (Portugal)". These normalize to the base language name
("portuguese") for example/pricing/context dict lookups, which are
shared across regional variants.

The full name (with region) is still passed to the LLM prompt so the
model knows which variant to produce.
"""
import re

_REGIONAL_SUFFIX = re.compile(r'\s*\([^)]*\)\s*')


def normalize_lang_key(language: str) -> str:
    """Normalize a language name to a lowercase base key for dict lookups.

    Strips regional suffixes in parentheses so that
    "Portuguese (Brazil)" and "Portuguese (Portugal)" both map to
    "portuguese", matching the shared dict keys used by example texts,
    pricing ratios, and context optimization.

    Examples:
        >>> normalize_lang_key("Portuguese (Brazil)")
        'portuguese'
        >>> normalize_lang_key("Portuguese (Portugal)")
        'portuguese'
        >>> normalize_lang_key("Portuguese")
        'portuguese'
        >>> normalize_lang_key("English")
        'english'
        >>> normalize_lang_key("")
        ''
    """
    if not language:
        return ""
    return _REGIONAL_SUFFIX.sub("", language).strip().lower()
