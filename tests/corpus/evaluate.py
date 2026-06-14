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
            "avg_duration_ms": sum(c["duration_ms"] for c in cases) // max(1, len(cases)),
        },
    }


def _check_thresholds(report: dict[str, Any]) -> list[str]:
    """Return non-empty list if any regression threshold is breached.

    Thresholds are calibrated on the current offline structural baseline:
    parse + reconstruct is expected to lose a small number of characters
    (whitespace/line-break normalisation) but must never drop terms.
    """
    failures: list[str] = []
    cases = report.get("cases") or []
    total_lost = sum(c["metrics"].get("chars_lost", 0) for c in cases)
    total_added = sum(c["metrics"].get("chars_added", 0) for c in cases)
    terms = sum(c["metrics"].get("terminology", {}).get("term_count", 0) for c in cases)
    preserved = sum(
        1
        for c in cases
        for t in c["metrics"].get("terminology", {}).get("terms", {}).values()
        if t.get("preserved")
    )
    # Structural regressions — allow whitespace normalisation up to ~100 chars.
    if total_lost > 100:
        failures.append(f"too many chars lost: {total_lost} > 100")
    if total_added > 100:
        failures.append(f"too many chars added: {total_added} > 100")
    # Terminology regressions — hard gate: every tracked term must survive.
    if terms and preserved < terms:
        failures.append(f"terminology not fully preserved: {preserved}/{terms}")
    return failures


def main() -> int:
    report = evaluate_all()
    failures = _check_thresholds(report)
    if failures:
        report["summary"]["regressions"] = failures
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
