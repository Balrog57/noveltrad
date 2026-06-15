"""Corpus evaluation — offline structural and quality checks.

Provides the ``evaluate_all()`` entrypoint used by
``test_corpus_evaluate.py``. Runs parse → chunk → assemble
round-trips on all corpus extracts and returns a JSON-serialisable
report.
"""

from __future__ import annotations

import time
import tempfile
from pathlib import Path
from typing import Any

from . import (
    ALL_EXTRACTS,
    structural_metrics,
    write_txt_fixture,
)

# Lazy imports to keep the module importable without the full stack
_CHUNK_PARAGRAPHS = None
_READ_DOCUMENT = None


def _lazy_imports() -> None:
    global _CHUNK_PARAGRAPHS, _READ_DOCUMENT
    if _CHUNK_PARAGRAPHS is not None:
        return
    from src.backend.formats import chunk_paragraphs, read_document  # type: ignore

    _CHUNK_PARAGRAPHS = chunk_paragraphs
    _READ_DOCUMENT = read_document


def _evaluate_extract(key: str, text: str) -> dict[str, Any]:
    """Run a single extract through parse → chunk and return metrics."""
    _lazy_imports()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = write_txt_fixture(key, root)
        doc = _READ_DOCUMENT(path)
        paragraphs = doc.chapters[0].paragraphs if doc.chapters else []
        chunks = _CHUNK_PARAGRAPHS(
            paragraphs,
            doc.chapters[0].id if doc.chapters else "ch0",
            doc.chapters[0].title if doc.chapters else "",
        )
        recon = " ".join(c["source_text"] for c in chunks)
        metrics = structural_metrics(text, recon)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "case_id": f"corpus/{key}",
        "format": "txt",
        "metrics": metrics,
        "warnings": [],
        "duration_ms": round(elapsed, 1),
        "tokens": {"input": 0, "output": 0},
        "estimated_cost_usd": 0.0,
    }


def evaluate_all() -> dict[str, Any]:
    """Run evaluation on every corpus extract and return a report dict."""
    cases = []
    for key, text in ALL_EXTRACTS.items():
        try:
            result = _evaluate_extract(key, text)
        except Exception as exc:
            result = {
                "case_id": f"corpus/{key}",
                "format": "txt",
                "error": str(exc),
                "duration_ms": 0,
                "tokens": {"input": 0, "output": 0},
                "estimated_cost_usd": 0.0,
            }
        cases.append(result)
    return {
        "schema_version": 1,
        "offline": True,
        "summary": {
            "case_count": len(cases),
            "cases_with_warnings": sum(
                1 for c in cases if c.get("warnings")
            ),
        },
        "cases": cases,
    }


if __name__ == "__main__":
    import json, sys

    report = evaluate_all()
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
