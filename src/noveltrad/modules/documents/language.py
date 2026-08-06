"""Source-language detection (SDD 10.6).

The Lingua detector receives at most 200,000 alphabetic characters of the
visible text, split equally between start, middle and end after removing
URLs, code blocks and markers. The ISO 639-1 code of the highest-confidence
candidate is returned, or "und" when no candidate exists.
"""

from __future__ import annotations

import re

from lingua import Language, LanguageDetectorBuilder

from .limits import MAX_LINGUA_CHARS

_URL_RE = re.compile(r"https?://\S+")
_CODE_FENCE_RE = re.compile(r"(?s)```.*?```|~~~.*?~~~")
_MARKER_RE = re.compile(r"\[NOVELTRAD:[0-9a-f]{16}\]")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        languages = (
            Language.ENGLISH,
            Language.FRENCH,
            Language.GERMAN,
            Language.SPANISH,
            Language.ITALIAN,
            Language.PORTUGUESE,
            Language.DUTCH,
            Language.POLISH,
            Language.RUSSIAN,
            Language.JAPANESE,
            Language.KOREAN,
            Language.CHINESE,
            Language.ARABIC,
            Language.TURKISH,
            Language.SWEDISH,
            Language.NYNORSK,
            Language.DANISH,
            Language.FINNISH,
            Language.CZECH,
            Language.UKRAINIAN,
            Language.ROMANIAN,
            Language.HUNGARIAN,
            Language.GREEK,
            Language.VIETNAMESE,
            Language.INDONESIAN,
            Language.THAI,
            Language.HINDI,
            Language.BENGALI,
            Language.HEBREW,
        )
        _detector = (
            LanguageDetectorBuilder.from_languages(*languages)
            .with_preloaded_language_models()
            .build()
        )
    return _detector


def _clean(text: str) -> str:
    text = _URL_RE.sub(" ", text)
    text = _CODE_FENCE_RE.sub(" ", text)
    text = _MARKER_RE.sub(" ", text)
    text = _COMMENT_RE.sub(" ", text)
    alphabetic = re.sub(
        r"[^A-Za-zÀ-ÿ\u0370-\u03FF\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", alphabetic).strip()


def detect_language(markdown: str) -> str:
    """Return an ISO 639-1 code or 'und'."""
    cleaned = _clean(markdown)
    if not cleaned:
        return "und"
    if len(cleaned) > MAX_LINGUA_CHARS:
        third = MAX_LINGUA_CHARS // 3
        cleaned = (
            cleaned[:third]
            + cleaned[len(cleaned) // 2 : len(cleaned) // 2 + third]
            + cleaned[-third:]
        )
    detector = _get_detector()
    confidence = detector.compute_language_confidence_values(cleaned)
    if not confidence:
        return "und"
    best = confidence[0]
    if best.value == 0.0:
        return "und"
    return best.language.iso_code_639_1.name.lower()
