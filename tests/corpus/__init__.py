"""Evaluation corpus for translation quality measurement.

Each extract represents a literary domain: dialogue, exposition,
description, notes, subtitles, and fantasy terms. The module provides
helpers to generate fixture files and evaluate structural integrity
(chunk → assemble → verify no text loss, order preserved).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# ---------- representative extracts ----------


CORPUS_DIALOGUE = """Chapter 1

"I can't believe you did that," she said, her voice trembling.

"I had no choice." He looked away. "The gate was already opening."

"But you promised! You stood right there and said—" She stopped, biting her lip.

A long silence filled the room. Outside, the wind rattled the shutters.
"""

CORPUS_EXPOSITION = """Chapter 2

The city of Aldervale had stood for three thousand years, its walls
built from stone quarried in the Age of Kings. Scholars disagreed on
the exact founding date — some pointed to the Treaty of the Four Rivers,
others to the coronation of Alaric the First — but all agreed that no
army had ever breached the Outer Gate.

Until today.
"""

CORPUS_DESCRIPTION = """Chapter 3

The garden stretched toward the horizon, a riot of crimson roses and
silver-leafed lavender. Stone paths wound between ancient oaks whose
branches formed a canopy so dense that only slivers of afternoon light
reached the moss below. A fountain stood at the center — a marble
nymph pouring an endless stream from a tilted amphora — and around it
hummed a thousand bees drunk on nectar.
"""

CORPUS_FANTASY_TERMS = """Chapter 4

The Veil-Walker raised his staff and whispered the Binding Words.
A ripple passed through the air, and the lesser demons — the skritch,
the hollow-men, the shade-hounds — fell silent. Only the Arch-Fiend
remained, its seven eyes fixed on the sorcerer.

"You cannot hold the Veil forever, mortal," it hissed.

"Perhaps not," said Talric. "But I only need to hold it long enough."
"""


# ---------- all extracts ----------


ALL_EXTRACTS: dict[str, str] = {
    "dialogue": CORPUS_DIALOGUE,
    "exposition": CORPUS_EXPOSITION,
    "description": CORPUS_DESCRIPTION,
    "fantasy_terms": CORPUS_FANTASY_TERMS,
}


# ---------- fixture generators ----------


def write_txt_fixture(extract_key: str, target_dir: Path) -> Path:
    """Write a TXT fixture file from an extract key, return path."""
    text = ALL_EXTRACTS.get(extract_key)
    if text is None:
        raise KeyError(f"Unknown extract: {extract_key!r}")
    path = target_dir / f"{extract_key}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def write_srt_fixture(extract_key: str, target_dir: Path, lines_per_cue: int = 1) -> Path:
    """Write a minimal SRT fixture from extract text, one cue per paragraph."""
    text = ALL_EXTRACTS.get(extract_key)
    if text is None:
        raise KeyError(f"Unknown extract: {extract_key!r}")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    cues: list[str] = []
    start_sec = 0
    for idx, para in enumerate(paragraphs, 1):
        cues.append(str(idx))
        end_sec = start_sec + max(2, len(para) // 15)
        cues.append(
            f"00:{start_sec // 60:02d}:{start_sec % 60:02d},000"
            f" --> "
            f"00:{end_sec // 60:02d}:{end_sec % 60:02d},000"
        )
        cues.append(para)
        cues.append("")
        start_sec = end_sec + 1
    path = target_dir / f"{extract_key}.srt"
    path.write_text("\n".join(cues), encoding="utf-8")
    return path


# ---------- evaluation helpers ----------


def structural_metrics(original: str, reconstructed: str) -> dict[str, Any]:
    """Compare original and reconstructed text for structural integrity.

    Return:
        chars_lost: number of characters missing from reconstructed
        chars_added: characters present in reconstructed but not original
        word_count_delta: difference in word count
        lines_count_delta: difference in line count
    """
    orig_words = original.split()
    recon_words = reconstructed.split()
    orig_chars = len(original)
    recon_chars = len(reconstructed)
    return {
        "chars_lost": max(0, orig_chars - recon_chars),
        "chars_added": max(0, recon_chars - orig_chars),
        "word_count_original": len(orig_words),
        "word_count_reconstructed": len(recon_words),
        "word_count_delta": len(recon_words) - len(orig_words),
        "line_count_original": len(original.splitlines()),
        "line_count_reconstructed": len(reconstructed.splitlines()),
    }


def terminology_coherence(
    source_text: str, translated_text: str, terms: list[str]
) -> dict[str, Any]:
    """Check if named entities / terms are preserved in the translation."""
    found: dict[str, bool] = {}
    for term in terms:
        in_source = term in source_text
        in_target = term in translated_text
        found[term] = {"in_source": in_source, "in_target": in_target, "preserved": in_target}
    all_preserved = all(v["preserved"] for v in found.values())
    return {"terms": found, "all_preserved": all_preserved, "term_count": len(terms)}
