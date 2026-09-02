"""Literary Refine+ quality heuristics (no embeddings / BERTScore).

Proxies for the Stack Overflow article's semantic / fluency / glossary /
entity gates. Used after Pass 1 and at final eval to decide accept vs one
targeted extra LLM call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from src.core.glossary.filter import filter_glossary
from src.core.refine.structure import PLACEHOLDER_RE, is_plain_text_structure_safe
from src.utils.lang_normalize import normalize_lang_key

# Literary thresholds (article 2, creative/literary column).
GLOSSARY_MATCH_MIN = 0.95
ENTITY_MATCH_REQUIRED = 1.0
MAX_LITERARY_OMISSIONS = 1
LENGTH_RATIO_MIN = 0.4
LENGTH_RATIO_MAX = 2.5
LENGTH_RATIO_CJK_MIN = 0.3
LENGTH_RATIO_CJK_MAX = 3.0
CJK_LEFTOVER_SPAN = 8

_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]")
_CJK_RUN_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]{2,}")
_DATE_RE = re.compile(
    r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b"
    r"|\b\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
    r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\.?\s+\d{2,4}\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(
    r"(?<!\[)\b\d{1,3}(?:[ ,.\u00a0]\d{3})+(?:[.,]\d+)?\b"
    r"|(?<!\[)\b\d+(?:[.,]\d+)?\b"
)
_UNIT_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|°[CFcF]|km/h|km|kg|mg|cm|mm|mL|ml|kPa|hPa|"
    r"Hz|kHz|MHz|mph|lb|oz)\b",
    re.IGNORECASE,
)

_LATIN_SCRIPT_TARGETS = frozenset({
    "english", "french", "spanish", "german", "italian", "portuguese",
    "dutch", "polish", "czech", "slovak", "romanian", "hungarian",
    "swedish", "norwegian", "danish", "finnish", "turkish", "indonesian",
    "vietnamese", "latin",
})

RETRY_PASS1 = "pass1"
RETRY_PASS2 = "pass2"
RETRY_PASS3 = "pass3"
RETRY_OMISSION = "omission"
ACCEPT = "accept"


@dataclass
class QualityReport:
    """One QA snapshot for a source/target pair."""

    numbers_ok: bool = True
    missing_numbers: List[str] = field(default_factory=list)
    extra_numbers: List[str] = field(default_factory=list)
    entities_ok: bool = True
    missing_entities: List[str] = field(default_factory=list)
    glossary_rate: float = 1.0
    glossary_ok: bool = True
    missing_glossary: List[str] = field(default_factory=list)
    placeholders_ok: bool = True
    structure_ok: bool = True
    fluency_ok: bool = True
    leftover_source_script: bool = False
    length_ratio: float = 1.0
    length_ok: bool = True
    omission_count: int = 0
    addition_count: int = 0

    def fidelity_ok(self) -> bool:
        return self.numbers_ok and self.entities_ok and self.placeholders_ok

    def to_log_dict(self) -> Dict[str, object]:
        return {
            "numbers_ok": self.numbers_ok,
            "missing_numbers": self.missing_numbers,
            "extra_numbers": self.extra_numbers,
            "entities_ok": self.entities_ok,
            "missing_entities": self.missing_entities,
            "glossary_rate": round(self.glossary_rate, 4),
            "glossary_ok": self.glossary_ok,
            "missing_glossary": self.missing_glossary,
            "placeholders_ok": self.placeholders_ok,
            "structure_ok": self.structure_ok,
            "fluency_ok": self.fluency_ok,
            "leftover_source_script": self.leftover_source_script,
            "length_ratio": round(self.length_ratio, 3),
            "length_ok": self.length_ok,
            "omission_count": self.omission_count,
            "addition_count": self.addition_count,
        }


def _normalize_digits(token: str) -> str:
    return re.sub(r"\D", "", token or "")


def extract_number_tokens(text: str) -> List[str]:
    """Dates, units, and digit groups, excluding placeholder ids."""
    cleaned = PLACEHOLDER_RE.sub(" ", text or "")
    found: List[str] = []
    seen_spans: List[Tuple[int, int]] = []
    for pattern in (_DATE_RE, _UNIT_RE, _NUMBER_RE):
        for match in pattern.finditer(cleaned):
            span = match.span()
            if any(span[0] >= a and span[1] <= b for a, b in seen_spans):
                continue
            token = match.group(0).strip()
            if token:
                found.append(token)
                seen_spans.append(span)
    return found


def _digit_multiset(tokens: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for token in tokens:
        key = _normalize_digits(token)
        if len(key) < 1:
            continue
        # Bare 0/1 in literary prose is too noisy as a fidelity gate.
        if key in {"0", "1"} and len(token) == 1:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def compare_numbers(source: str, target: str) -> Tuple[bool, List[str], List[str]]:
    src = _digit_multiset(extract_number_tokens(source))
    tgt = _digit_multiset(extract_number_tokens(target))
    missing: List[str] = []
    extra: List[str] = []
    for key, count in src.items():
        have = tgt.get(key, 0)
        if have < count:
            missing.extend([key] * (count - have))
    for key, count in tgt.items():
        have = src.get(key, 0)
        if have < count:
            extra.extend([key] * (count - have))
    return (not missing and not extra), missing, extra


def glossary_hits_in_text(
    text: str,
    glossary_terms: Optional[Dict[str, str]],
) -> Dict[str, str]:
    if not text or not glossary_terms:
        return {}
    filtered, _capped = filter_glossary(text, glossary_terms)
    return dict(filtered)


def _target_present(translation: str, target_term: str) -> bool:
    hay = translation or ""
    needle = (target_term or "").strip()
    if not needle:
        return True
    if needle.lower() in hay.lower():
        return True
    # Inflected / spaced variants: require the longest token of the target.
    tokens = [t for t in re.split(r"\s+", needle) if len(t) >= 4]
    if tokens and all(t.lower() in hay.lower() for t in tokens):
        return True
    return False


def glossary_match_rate(
    source: str,
    translation: str,
    glossary_terms: Optional[Dict[str, str]],
) -> Tuple[float, List[str]]:
    hits = glossary_hits_in_text(source, glossary_terms)
    if not hits:
        return 1.0, []
    missing: List[str] = []
    matched = 0
    for source_term, target_term in hits.items():
        if _target_present(translation, target_term):
            matched += 1
        else:
            missing.append(f"{source_term}->{target_term}")
    return matched / len(hits), missing


def _is_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def length_ratio(source: str, target: str) -> float:
    src = re.sub(r"\s+", "", source or "")
    tgt = re.sub(r"\s+", "", target or "")
    if not src:
        return 1.0
    return len(tgt) / max(1, len(src))


def length_ratio_ok(source: str, target: str) -> Tuple[bool, float]:
    ratio = length_ratio(source, target)
    cjk = _is_cjk(source) or _is_cjk(target)
    lo, hi = (
        (LENGTH_RATIO_CJK_MIN, LENGTH_RATIO_CJK_MAX)
        if cjk
        else (LENGTH_RATIO_MIN, LENGTH_RATIO_MAX)
    )
    return lo <= ratio <= hi, ratio


def leftover_source_script(
    source: str,
    target: str,
    target_language: str = "",
) -> bool:
    """True when a Latin-script target still contains a long source-script span."""
    lang = normalize_lang_key(target_language)
    if lang and lang not in _LATIN_SCRIPT_TARGETS:
        return False
    if not _is_cjk(source):
        return False
    for run in _CJK_RUN_RE.findall(target or ""):
        if len(run) >= CJK_LEFTOVER_SPAN and run not in (source or ""):
            return True
        if len(run) >= CJK_LEFTOVER_SPAN and run in (source or ""):
            return True
    return False


def placeholders_match(previous: str, candidate: str) -> bool:
    before = sorted(PLACEHOLDER_RE.findall(previous or ""))
    after = sorted(PLACEHOLDER_RE.findall(candidate or ""))
    return before == after


def evaluate_pair(
    source: str,
    translation: str,
    *,
    previous: Optional[str] = None,
    glossary_terms: Optional[Dict[str, str]] = None,
    target_language: str = "",
    check_structure: bool = True,
) -> QualityReport:
    """Run all Refine+ heuristics on one aligned pair."""
    report = QualityReport()
    numbers_ok, missing_n, extra_n = compare_numbers(source, translation)
    report.numbers_ok = numbers_ok
    report.missing_numbers = missing_n
    report.extra_numbers = extra_n

    rate, missing_g = glossary_match_rate(source, translation, glossary_terms)
    report.glossary_rate = rate
    report.glossary_ok = rate + 1e-9 >= GLOSSARY_MATCH_MIN
    report.missing_glossary = missing_g
    # Factual entities (numbers/dates/units) must be 100%. Glossary names use
    # the literary ≥95% gate below, not a second 100% list.
    report.entities_ok = numbers_ok
    report.missing_entities = list(missing_n)

    report.placeholders_ok = placeholders_match(previous or translation, translation)
    if check_structure and previous is not None:
        report.structure_ok = is_plain_text_structure_safe(previous, translation)
    else:
        report.structure_ok = True

    leftover = leftover_source_script(source, translation, target_language)
    report.leftover_source_script = leftover
    report.fluency_ok = (not leftover) and report.structure_ok

    length_ok, ratio = length_ratio_ok(source, translation)
    report.length_ok = length_ok
    report.length_ratio = ratio

    # Factual omissions: missing numbers. Non-factual literary slack is not
    # counted here (the LLM omission pass handles prose gaps).
    report.omission_count = len(missing_n) + len(missing_g)
    report.addition_count = len(extra_n)
    return report


def decide_retry(report: QualityReport, *, extra_used: bool) -> str:
    """Return ACCEPT or a retry kind. One extra max is enforced by the caller."""
    if extra_used:
        return ACCEPT
    if not report.numbers_ok or report.extra_numbers:
        return RETRY_PASS1
    if not report.entities_ok:
        return RETRY_PASS1
    if not report.glossary_ok:
        return RETRY_PASS3
    if not report.fluency_ok or report.leftover_source_script:
        return RETRY_PASS2
    if report.omission_count > MAX_LITERARY_OMISSIONS:
        return RETRY_OMISSION
    return ACCEPT


def glossary_terms_from_options(prompt_options: Optional[dict]) -> Dict[str, str]:
    if not prompt_options:
        return {}
    terms = prompt_options.get("glossary_terms") or {}
    return dict(terms) if isinstance(terms, dict) else {}


def has_glossary_hits(
    source: str,
    draft: str,
    prompt_options: Optional[dict],
) -> bool:
    terms = glossary_terms_from_options(prompt_options)
    if not terms:
        return False
    lookup = "\n".join(part for part in (source or "", draft or "") if part.strip())
    return bool(glossary_hits_in_text(lookup, terms))


def format_decision_log(
    segment_index: int,
    pass_name: str,
    decision: str,
    report: QualityReport,
) -> str:
    return (
        f"Refine+ segment {segment_index} after {pass_name}: "
        f"decision={decision} glossary={report.glossary_rate:.0%} "
        f"numbers_ok={report.numbers_ok} fluency_ok={report.fluency_ok}"
    )
