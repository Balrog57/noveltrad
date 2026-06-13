"""Deterministic corpus evaluator for NovelTrad.

The runner only parses local fixtures and computes structural metrics.
It never calls LLM providers, cloud APIs, or the GUI.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from src.backend.formats import read_document

from . import (
    ALL_EXTRACTS,
    CORPUS_CASES,
    CorpusCase,
    structural_metrics,
    terminology_coherence,
    write_case_fixture,
)


def evaluate_case(case: CorpusCase, root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    fixture = write_case_fixture(case, root)
    doc = read_document(fixture)
    reconstructed = "\n\n".join(
        paragraph
        for chapter in doc.chapters
        for paragraph in chapter.paragraphs
    )
    original = ALL_EXTRACTS[case.extract_key]
    metrics = structural_metrics(original, reconstructed)
    term_metrics = terminology_coherence(original, reconstructed, list(case.terms))
    warnings: list[str] = []
    if metrics["word_count_reconstructed"] == 0:
        warnings.append("empty_reconstruction")
    if metrics["word_count_delta"] < -3:
        warnings.append("possible_word_loss")
    if case.terms and not term_metrics["all_preserved"]:
        warnings.append("terminology_not_preserved")
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "case_id": case.case_id,
        "format": case.source_format,
        "metrics": {
            **metrics,
            "terminology": term_metrics,
        },
        "warnings": warnings,
        "duration_ms": duration_ms,
        "tokens": {"input": 0, "output": 0},
        "estimated_cost_usd": 0.0,
    }


def evaluate_all() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cases = [evaluate_case(case, root) for case in CORPUS_CASES]
    return {
        "schema_version": 1,
        "offline": True,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "warning_count": sum(len(case["warnings"]) for case in cases),
        },
    }


def main() -> int:
    print(json.dumps(evaluate_all(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
