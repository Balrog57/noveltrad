"""Corpus test fixtures for structural and quality evaluation.

Provides representative literary extracts for round-trip testing
of the parse → chunk → assemble pipeline.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

# --- Extracts keyed by type ---

ALL_EXTRACTS: dict[str, str] = {
    "dialogue": (
        '"I can\'t believe you did that," she said.\n'
        '"The gate was already opening," he replied.\n'
        "A long silence filled the room.\n"
    ),
    "exposition": (
        "The town of Aldervale had changed little since the signing "
        "of the Treaty of the Four Rivers. Cobblestone streets still "
        "wound between timber-framed houses. The old oak at the crossroads "
        "still spread its branches over the market square. Until today, "
        "the elders said, nothing ever happened here.\n"
    ),
    "description": (
        "The garden was a riot of crimson roses and climbing jasmine. "
        "A marble nymph stood at the centre of the reflecting pool, "
        "water trickling from her outstretched hand. The air hummed "
        "with the sound of a thousand bees.\n"
    ),
    "fantasy_terms": (
        "The Veil-Walker spoke to Talric about the Arch-Fiend. "
        "Binding Words were exchanged, each syllable cutting the air "
        "like a blade. The Veil itself rippled at their power.\n"
    ),
    "narrative": (
        "He walked for three days through the Ash Wastes. "
        "The sun was a dim orange disc behind the perpetual haze. "
        "On the fourth morning he saw the tower.\n"
    ),
    "technical": (
        "The API endpoint returns a JSON object with the following "
        "keys: status, data, and pagination. The max page size is 100.\n"
    ),
}


def structural_metrics(original: str, reconstructed: str) -> dict[str, Any]:
    """Compare original and reconstructed text, return structural metrics."""
    orig_words = len(original.split())
    recon_words = len(reconstructed.split())
    return {
        "chars_lost": max(0, len(original) - len(reconstructed)),
        "chars_added": max(0, len(reconstructed) - len(original)),
        "word_count_delta": recon_words - orig_words,
        "chars_original": len(original),
        "chars_reconstructed": len(reconstructed),
        "words_original": orig_words,
        "words_reconstructed": recon_words,
    }


def terminology_coherence(
    source: str, translated: str, terms: list[str]
) -> dict[str, Any]:
    """Check if all specified terms appear in both source and translation."""
    all_preserved = all(t in translated for t in terms)
    missing = [t for t in terms if t not in translated]
    return {
        "all_preserved": all_preserved,
        "missing": missing,
        "preserved_count": len(terms) - len(missing),
        "total_terms": len(terms),
    }


def write_txt_fixture(key: str, root: Path) -> Path:
    """Write a TXT fixture for the given extract key to *root*."""
    text = ALL_EXTRACTS.get(key, "")
    path = root / f"{key}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def write_srt_fixture(key: str, root: Path) -> Path:
    """Write a minimal SRT fixture for the given extract key."""
    text = ALL_EXTRACTS.get(key, "Empty.")
    lines = [
        "1",
        "00:00:01,000 --> 00:00:05,000",
        text.strip(),
        "",
    ]
    path = root / f"{key}.srt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


__all__ = [
    "ALL_EXTRACTS",
    "structural_metrics",
    "terminology_coherence",
    "write_txt_fixture",
    "write_srt_fixture",
]
