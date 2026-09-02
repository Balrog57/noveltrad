"""Literary Refine+ heuristics: numbers, glossary ≥95%, omissions, additions."""
from src.core.refine.quality_checks import (
    ACCEPT,
    MAX_LITERARY_OMISSIONS,
    RETRY_OMISSION,
    RETRY_PASS1,
    RETRY_PASS2,
    RETRY_PASS3,
    QualityReport,
    compare_numbers,
    decide_retry,
    evaluate_pair,
    leftover_source_script,
)


def test_omitted_number_fails_fidelity():
    source = "She turned 17 in 2012."
    translation = "She came of age that year."
    ok, missing, extra = compare_numbers(source, translation)
    assert ok is False
    assert missing
    assert not extra
    report = evaluate_pair(source, translation, target_language="English")
    assert report.numbers_ok is False
    assert report.fidelity_ok() is False
    assert decide_retry(report, extra_used=False) == RETRY_PASS1


def test_factual_addition_is_refused():
    source = "She smiled at him."
    translation = "She smiled at him and 99 soldiers."
    report = evaluate_pair(source, translation, target_language="English")
    assert report.extra_numbers
    assert report.addition_count >= 1
    assert decide_retry(report, extra_used=False) == RETRY_PASS1


def test_glossary_below_95_percent_retries_pass3():
    source = "Alice talked to Bob and Carol at noon."
    translation = "Alice talked to Bob at noon."
    glossary = {"Alice": "Alice", "Bob": "Bob", "Carol": "Carol"}
    report = evaluate_pair(
        source, translation, glossary_terms=glossary, target_language="English",
    )
    assert report.glossary_rate < 0.95
    assert report.glossary_ok is False
    assert decide_retry(report, extra_used=False) == RETRY_PASS3


def test_glossary_all_hits_is_ok():
    source = "Alice talked to Bob."
    translation = "Alice spoke with Bob."
    glossary = {"Alice": "Alice", "Bob": "Bob"}
    report = evaluate_pair(
        source, translation, glossary_terms=glossary, target_language="English",
    )
    assert report.glossary_ok is True
    assert report.glossary_rate == 1.0


def test_one_literary_omission_is_tolerated():
    report = QualityReport(omission_count=MAX_LITERARY_OMISSIONS)
    assert decide_retry(report, extra_used=False) == ACCEPT


def test_two_literary_omissions_retry_omission_qa():
    report = QualityReport(omission_count=MAX_LITERARY_OMISSIONS + 1)
    assert decide_retry(report, extra_used=False) == RETRY_OMISSION


def test_extra_already_used_always_accepts():
    report = QualityReport(numbers_ok=False, extra_numbers=["42"], glossary_ok=False)
    assert decide_retry(report, extra_used=True) == ACCEPT


def test_leftover_cjk_in_latin_target_fails_fluency():
    source = "这是一段足够长的中文原文句子。"
    translation = "A draft that still contains 这是一段足够长的中文原文句子。"
    assert leftover_source_script(source, translation, "English") is True
    report = evaluate_pair(source, translation, target_language="English")
    assert report.fluency_ok is False
    assert decide_retry(report, extra_used=False) == RETRY_PASS2
