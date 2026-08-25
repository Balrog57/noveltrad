"""
Build the glossary block to inject into the system prompt.

The block style mirrors the existing prompt voice in src/prompts/prompts.py
(numbered priorities, MANDATORY phrasing) so the LLM treats glossary entries
with the same weight as the rest of the instructions.

Two blocks live here:

- ``build_glossary_block`` renders the terms that match the current chunk.
- ``build_cast_block`` renders every gendered entity in the glossary,
  regardless of the current chunk. Gender is the one piece of glossary data
  that is needed precisely when the term is *absent*: in languages that omit
  the subject or do not mark gender (Chinese, Japanese, Korean, Turkish,
  Finnish), a passage can be full of pronouns without naming anyone, and a
  chunk-filtered glossary says nothing there. That is exactly where a model
  falls back to masculine for everyone.
"""
from typing import Dict, List, Optional, Set, Tuple

from src.core.glossary.filter import filter_glossary
from src.core.glossary.inflection import target_language_is_inflected
from src.core.glossary.models import DEFAULT_MAX_CAST_ENTRIES, GlossaryConfig, normalize_gender

# Target-side counterpart of the '|' source-variants line: in an inflected
# target the citation form listed in the glossary is routinely NOT the form a
# grammatical sentence needs, so "EXACT" has to be scoped to the choice of
# rendering rather than to the letters. Emitted as a single line, only for the
# languages in INFLECTED_TARGET_LANGUAGES.
#
# It grants the whole morphology on purpose, rather than "keep the stem,
# inflect the ending": that narrower licence is false for several of the gated
# languages (Turkish kitap->kitabı, Finnish katu->kadun, Russian отец->отца,
# German Vater->Väter) and would not cover derivation, which is where the drift
# reported in issue #255 actually shows up.
TARGET_INFLECTION_INSTRUCTION = (
    "Each target above is given in its dictionary form. Apply whatever "
    "morphological changes {target_language} grammar requires — case, number, "
    "agreement, derived forms, and the regular stem alternations these entail. "
    "What must never change is the choice of rendering: do not substitute a "
    "different translation, a different transliteration, or a more familiar "
    "variant of the term."
)


def build_glossary_block(
    filtered_terms: Dict[str, str],
    target_language: str = "",
    term_metadata: Optional[Dict[str, Dict[str, str]]] = None,
) -> str:
    """
    Render the glossary block. Empty string if no terms.

    Args:
        filtered_terms: {source: target} of terms that match the current chunk.
        target_language: selects the target-side inflection instruction, emitted
            only for the languages in ``INFLECTED_TARGET_LANGUAGES``. The
            exclusion criterion (does inflection change the written form of the
            term?) is documented in ``src/core/glossary/inflection.py``.
        term_metadata: optional {source: {category, gender}} mapping. When a
            term has a category, it is rendered as a bracketed hint after the
            arrow so the LLM can disambiguate homonyms (e.g. a name vs a
            place sharing the same spelling). A gender is appended to the same
            hint; the authoritative gender instruction lives in the cast block
            built by ``build_cast_block``.

    The block lives between the optional sections and the placeholder section
    in the system prompt — close enough to the input text that the model will
    not forget it, but not after the FINAL REMINDER so the output-language
    reminder stays last.
    """
    if not filtered_terms:
        return ""

    metadata = term_metadata or {}

    lines = [
        "# GLOSSARY - REQUIRED TRANSLATIONS",
        "",
        "MANDATORY: use these EXACT translations whenever the source term appears.",
        "Do NOT paraphrase, transliterate differently, or invent alternatives.",
        *([TARGET_INFLECTION_INSTRUCTION.format(target_language=target_language)]
          if target_language_is_inflected(target_language) else []),
        "Apply each rule consistently every time the term occurs.",
        "When several source forms are listed before the arrow (comma-separated), they are inflected variants of the same entity — translate any of them with the single target on the right.",
        "Bracketed hints after the arrow (e.g. [character, female]) describe the entity type and, where known, its gender — use them to disambiguate and to pick pronouns, never as part of the translation.",
        "",
    ]

    for source, target in filtered_terms.items():
        meta = metadata.get(source) or {}
        category = (meta.get("category") or "").strip()
        gender = normalize_gender(meta.get("gender"))
        # Render alternatives (declined forms separated by '|' in storage) as
        # a comma-separated list so the LLM reads them as a natural set.
        display_source = ", ".join(
            a.strip() for a in source.split("|") if a.strip()
        ) or source
        hints = [h for h in (category, gender) if h]
        if hints:
            lines.append(f"  - {display_source} -> {target}  [{', '.join(hints)}]")
        else:
            lines.append(f"  - {display_source} -> {target}")

    return "\n".join(lines) + "\n"


def build_cast_block(
    glossary_terms: Dict[str, str],
    term_metadata: Optional[Dict[str, Dict[str, str]]] = None,
    max_entries: int = DEFAULT_MAX_CAST_ENTRIES,
    chunk_content: str = "",
    matched_sources: Optional[Set[str]] = None,
) -> Tuple[str, bool]:
    """
    Render the cast block listing entities with a known gender.

    Unlike the glossary block, this is not limited to names that appear in the
    current chunk: a passage that refers to a character only by pronoun has no
    glossary match, yet that is exactly where the model would guess the gender.

    When ``chunk_content`` is set and the cast is larger than ``max_entries``,
    names that actually occur in the chunk are kept first, then the remaining
    slots are filled in glossary order so pronoun-only references still have a
    stable core cast. Without chunk text the list stays in glossary order
    (byte-identical across calls — used by tests and by callers that inject
    one global block).

    Args:
        glossary_terms: {source: target} for the whole glossary (unfiltered).
        term_metadata: {source: {category, gender}}. Entries whose gender is
            absent or unrecognized are skipped.
        max_entries: cap on the number of listed entities. The block is
            injected into every chunk, so an unbounded cast on a 300-character
            saga would be a permanent token tax.
        chunk_content: optional source text of the current chunk. Used only
            to prioritize which names survive the cap.
        matched_sources: optional pre-filtered source keys from a prior
            ``filter_glossary`` call. When provided with a capped cast, skips
            a second full-chunk glossary scan.

    Returns:
        (block, capped). ``block`` is "" when no entity has a known gender —
        which is the case for every glossary predating this field, so the
        injected prompt is unchanged until someone fills a gender in.
    """
    metadata = term_metadata or {}
    if not glossary_terms or not metadata:
        return "", False

    entries: List[Tuple[str, str, str, str]] = []
    for source, target in glossary_terms.items():
        gender = normalize_gender((metadata.get(source) or {}).get("gender"))
        if not gender:
            continue
        # The first alternative is the canonical form; listing every declined
        # variant here would triple the block for no gain, since the variants
        # are already spelled out in the glossary block.
        canonical = next(
            (a.strip() for a in source.split("|") if a.strip()),
            source,
        )
        entries.append((source, canonical, target, gender))

    if not entries:
        return "", False

    capped = False
    if max_entries and len(entries) > max_entries:
        capped = True
        in_chunk_keys: Set[str] = set()
        if matched_sources is not None:
            in_chunk_keys = matched_sources
        elif chunk_content:
            gendered_terms = {source: target for source, _, target, _ in entries}
            matched, _ = filter_glossary(
                chunk_content,
                gendered_terms,
                GlossaryConfig(max_entries=0, warn_on_cap=False),
            )
            in_chunk_keys = set(matched)
        preferred = [e for e in entries if e[0] in in_chunk_keys]
        filler = [e for e in entries if e[0] not in in_chunk_keys]
        entries = (preferred + filler)[:max_entries]

    lines = [
        "# CAST - CHARACTER GENDERS",
        "",
        "MANDATORY: each entity below has a fixed gender for the entire text.",
        "Use pronouns and gendered agreement matching the gender listed here, "
        "even when the source passage omits the subject or does not mark gender.",
        "Never default to masculine for an entity listed as female, and never "
        "switch an entity's gender between passages.",
        "This list is the reference for the whole work — an entity may be "
        "referred to here by pronoun only in the passage you are translating.",
        "",
    ]
    for _source, canonical, target, gender in entries:
        label = f"{canonical} ({target})" if target and target != canonical else canonical
        lines.append(f"  - {label} — {gender}")

    return "\n".join(lines) + "\n", capped
