"""Tests for glossary import (CDC F2.c).

Covers all three accepted shapes:
  - flat JSON map (the CDC example {"bug": "anomalie"})
  - JSON list of objects
  - CSV / TSV
"""

import json
from pathlib import Path

import pytest

from src.core.glossary import GlossaryError, load_glossary, parse_glossary_text


def test_parse_flat_json_map_cdc_example() -> None:
    """The exact CDC example shape must work."""
    g = parse_glossary_text('{"bug": "anomalie"}', "json")
    assert g == {"bug": "anomalie"}


def test_parse_flat_json_map_multiple_terms() -> None:
    g = parse_glossary_text('{"bug": "anomalie", "deploy": "déploiement"}', "json")
    assert g == {"bug": "anomalie", "deploy": "déploiement"}


def test_parse_json_list_of_objects() -> None:
    g = parse_glossary_text(
        json.dumps([{"term": "bug", "translation": "anomalie"},
                    {"term": "log", "translation": "journal"}]),
        "json",
    )
    assert g == {"bug": "anomalie", "log": "journal"}


def test_parse_json_list_alt_keys() -> None:
    g = parse_glossary_text('[{"source": "bug", "target": "anomalie"}]', "json")
    assert g == {"bug": "anomalie"}


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(GlossaryError):
        parse_glossary_text("{not json", "json")


def test_parse_json_wrong_type_raises() -> None:
    with pytest.raises(GlossaryError):
        parse_glossary_text('"just a string"', "json")


def test_parse_csv_with_header(tmp_path: Path) -> None:
    f = tmp_path / "g.csv"
    f.write_text("term,translation\nbug,anomalie\ndeploy,déploiement\n", encoding="utf-8")
    g = load_glossary(f)
    assert g == {"bug": "anomalie", "deploy": "déploiement"}


def test_parse_csv_without_header() -> None:
    g = parse_glossary_text("bug,anomalie\ndeploy,déploiement\n", "csv")
    assert g == {"bug": "anomalie", "deploy": "déploiement"}


def test_parse_tsv() -> None:
    g = parse_glossary_text("bug\tanomalie\ndeploy\tdéploiement\n", "tsv")
    assert g == {"bug": "anomalie", "deploy": "déploiement"}


def test_load_glossary_json_file(tmp_path: Path) -> None:
    f = tmp_path / "g.json"
    f.write_text('{"bug": "anomalie"}', encoding="utf-8")
    assert load_glossary(f) == {"bug": "anomalie"}


def test_load_glossary_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(GlossaryError):
        load_glossary(tmp_path / "nope.json")


def test_load_glossary_utf8_bom(tmp_path: Path) -> None:
    """utf-8-sig should tolerate a BOM written by some Windows editors."""
    f = tmp_path / "g.csv"
    f.write_bytes(b"\xef\xbb\xbfterm,translation\nbug,anomalie\n")
    assert load_glossary(f) == {"bug": "anomalie"}
