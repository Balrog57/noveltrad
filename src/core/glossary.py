"""Glossary loading & import.

CDC F2.c: load a JSON/CSV file of specific terms imposed on agents.
The CDC example shape is a flat mapping {"bug": "anomalie"}.

This module accepts all three common shapes and normalises them to a plain
dict[str, str] consumable by the pipeline state:

  1. Flat JSON map (CDC example)   {"bug": "anomalie", "deploy": "déploiement"}
  2. JSON list of objects          [{"term": "bug", "translation": "anomalie"}, ...]
  3. CSV / TSV                     term,translation\\nbug,anomalie
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path


class GlossaryError(ValueError):
    """Raised when a glossary file cannot be parsed."""


def load_glossary(path: str | Path) -> dict[str, str]:
    """Load a glossary file (JSON/CSV/TSV) into a flat dict[str, str].

    Format is inferred from the extension (.json / .csv / .tsv). Unknown
    extensions default to CSV.
    """
    p = Path(path)
    if not p.exists():
        raise GlossaryError(f"Glossary file not found: {p}")

    text = p.read_text(encoding="utf-8-sig")  # utf-8-sig tolerates a BOM
    suffix = p.suffix.lower()

    if suffix == ".json":
        return _parse_json(text)
    if suffix == ".tsv":
        return _parse_delimited(text, delimiter="\t")
    # default: CSV
    return _parse_delimited(text, delimiter=",")


def parse_glossary_text(text: str, fmt: str = "json") -> dict[str, str]:
    """Parse glossary content from an in-memory string (used by tests & IPC)."""
    if fmt == "json":
        return _parse_json(text)
    if fmt == "tsv":
        return _parse_delimited(text, delimiter="\t")
    if fmt == "csv":
        return _parse_delimited(text, delimiter=",")
    raise GlossaryError(f"Unsupported glossary format: {fmt}")


def _parse_json(text: str) -> dict[str, str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GlossaryError(f"Invalid JSON glossary: {exc}") from exc

    if isinstance(data, dict):
        # Shape 1: flat map {"bug": "anomalie"} (CDC example) — accept only str values.
        return {str(k): str(v) for k, v in data.items()}
    if isinstance(data, list):
        # Shape 2: list of objects [{term, translation}, ...]
        out: dict[str, str] = {}
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise GlossaryError(f"Glossary entry #{i} is not an object: {item!r}")
            term = item.get("term") or item.get("source") or item.get("key")
            translation = (
                item.get("translation") or item.get("target") or item.get("value")
            )
            if term is None or translation is None:
                raise GlossaryError(
                    f"Glossary entry #{i} missing term/translation: {item!r}"
                )
            out[str(term)] = str(translation)
        return out
    raise GlossaryError(f"JSON glossary must be an object or an array, got {type(data).__name__}")


def _parse_delimited(text: str, delimiter: str) -> dict[str, str]:
    """Parse a CSV/TSV with an optional header row term,translation."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    # O(1) memory iterator instead of loading all rows into a list
    row_iter = (row for row in reader if row and any(cell.strip() for cell in row))

    try:
        first = next(row_iter)
    except StopIteration:
        return {}

    out: dict[str, str] = {}
    # Detect header: treat as header ONLY if BOTH first and second cells look
    # like header names. Otherwise a legitimate term named "source"/"key"/"term"
    # in the first row would be wrongly skipped.
    term_headers = {"term", "source", "key", "source_term"}
    trans_headers = {"translation", "target", "value", "target_term"}
    header_like = (
        len(first) >= 2
        and first[0].strip().lower() in term_headers
        and first[1].strip().lower() in trans_headers
    )

    if not header_like and len(first) >= 2:
        term = first[0].strip()
        if term:
            out[term] = first[1].strip()

    for row in row_iter:
        if len(row) < 2:
            continue  # skip malformed lines
        term = row[0].strip()
        translation = row[1].strip()
        if term:
            out[term] = translation
    return out
