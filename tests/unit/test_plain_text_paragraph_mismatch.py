"""
Issue #253: a paragraph-count mismatch must become visible, then be repaired.

When the LLM returns fewer (or more) paragraphs than a segment covers,
_reconcile_paragraph_counts pads or merges silently, and the padded slots fall
back to source text in the rebuilt body — which is how source paragraphs end up
sitting right under their own translation on a run whose log is perfectly clean.

Phase 1 counted the mismatch, logged it, and marked the blocks that ended up
carrying source text. Phase 3 adds the repair: a mismatched segment is
re-translated one LLM call per paragraph, which makes the alignment exact by
construction (never a similarity-based realignment). The Phase 1 tests that
pinned "the output paragraphs are what they always were" are updated below to
the repaired output — that change of output is precisely what Phase 3 delivers.
"""
import re

import pytest
from lxml import etree

import src.core.common.plain_text_pipeline as plain_pipeline
from src.core.epub.plain_extractor import (
    extract_plain_paragraphs,
    replace_body_with_paragraphs,
)
from src.core.epub.translation_metrics import TranslationMetrics


MERGED = ["Alpha paragraph.", "Beta paragraph."]


def _fake_perfect_llm(prefix="T::"):
    """A fake LLM that translates each paragraph of the blob 1:1."""
    async def fake_request(*, main_content, **kwargs):
        paragraphs = re.split(r"\n{2,}", main_content)
        return "\n\n".join(
            (prefix + p) if p.strip() else p for p in paragraphs
        )
    return fake_request


def _fake_merging_llm(prefix="T::"):
    """A fake LLM that folds every paragraph of the blob into a single one."""
    async def fake_request(*, main_content, **kwargs):
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", main_content) if p.strip()]
        return prefix + " ".join(paragraphs)
    return fake_request


def _fake_single_newline_llm(prefix="T::"):
    """A fake LLM that separates paragraphs with a single newline."""
    async def fake_request(*, main_content, **kwargs):
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", main_content) if p.strip()]
        return "\n".join(prefix + p for p in paragraphs)
    return fake_request


def _recording_merging_llm(prefix="T::", fail_on=()):
    """Merging LLM that records its calls, for the repair tests.

    A multi-paragraph blob comes back folded into one paragraph (the #253
    failure mode); a single-paragraph repair call comes back 1:1, unless its
    source text is listed in `fail_on`, in which case it returns None.
    Every call is recorded as {'main', 'before', 'after'}.
    """
    calls = []

    async def fake_request(*, main_content, context_before="", context_after="", **kwargs):
        calls.append({
            'main': main_content,
            'before': context_before,
            'after': context_after,
        })
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", main_content) if p.strip()]
        if len(paragraphs) > 1:
            return prefix + " ".join(paragraphs)
        if main_content.strip() in fail_on:
            return None
        return prefix + main_content.strip()

    fake_request.calls = calls
    return fake_request


def _fake_always_splitting_llm(prefix="T::"):
    """A fake LLM that answers every call with two paragraphs, repair included.

    Used to prove the repair is attempted once: the surplus paragraph of a
    single-paragraph repair call is collapsed back with a space, never
    re-repaired.
    """
    calls = []

    async def fake_request(*, main_content, **kwargs):
        calls.append(main_content)
        body = " ".join(p.strip() for p in re.split(r"\n{2,}", main_content) if p.strip())
        return f"{prefix}{body}\n\nEXTRA"

    fake_request.calls = calls
    return fake_request


def _repair_failure_logs(logs):
    return [msg for key, msg in logs if key == "plain_text_paragraph_repair_failed"]


async def _run(paragraphs, max_tokens=1000, workers=1, **overrides):
    """Translate `paragraphs` and return (output, stats, logs)."""
    logs = []
    kwargs = dict(
        paragraphs=paragraphs,
        source_language="English",
        target_language="French",
        model_name="m",
        llm_client=object(),
        max_tokens_per_chunk=max_tokens,
        parallel_workers=workers,
        log_callback=lambda key, msg: logs.append((key, msg)),
    )
    kwargs.update(overrides)
    out, stats, interrupted = await plain_pipeline.translate_paragraphs_plain(**kwargs)
    assert not interrupted
    return out, stats, logs


def _mismatch_logs(logs):
    return [msg for key, msg in logs if key == "plain_text_paragraph_mismatch"]


# ---------------------------------------------------------------------------
# The detection helper
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_matching_count_is_not_flagged(monkeypatch):
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", _fake_perfect_llm())
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    assert plain_pipeline._paragraph_count_mismatch("A\n\nB", 2) is None
    assert plain_pipeline._paragraph_count_mismatch("A", 1) is None

    out, stats, logs = await _run(MERGED)

    assert out == [f"T::{p}" for p in MERGED]
    assert stats.paragraph_count_mismatches == 0
    assert _mismatch_logs(logs) == []


@pytest.mark.asyncio
async def test_merged_paragraphs_are_flagged_and_logged(monkeypatch):
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", _fake_merging_llm())
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    assert plain_pipeline._paragraph_count_mismatch("A\nB", 2) == (1, 2)
    assert plain_pipeline._paragraph_count_mismatch("", 2) == (0, 2)

    out, stats, logs = await _run(MERGED)

    # The mismatch is still detected and logged once; since phase 3 the segment
    # is then re-translated paragraph by paragraph instead of being padded, so
    # no slot is left empty.
    assert out == ["T::Alpha paragraph.", "T::Beta paragraph."]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    messages = _mismatch_logs(logs)
    assert len(messages) == 1
    assert "1" in messages[0] and "2" in messages[0]


@pytest.mark.asyncio
async def test_single_newline_separator_is_flagged(monkeypatch):
    """The model kept the paragraphs but joined them with one newline."""
    monkeypatch.setattr(
        plain_pipeline, "generate_translation_request", _fake_single_newline_llm()
    )
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    assert plain_pipeline._paragraph_count_mismatch("A\n\nB\n\nC", 2) == (3, 2)

    source = ["First one.", "Second one.", "Third one."]
    out, stats, logs = await _run(source)

    # Detected as one paragraph instead of three, then repaired: each source
    # paragraph is re-translated on its own and lands in its own slot.
    assert out == ["T::First one.", "T::Second one.", "T::Third one."]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    assert len(_mismatch_logs(logs)) == 1


@pytest.mark.asyncio
async def test_partial_segments_are_never_flagged(monkeypatch):
    """An oversized paragraph is split into pieces that are joined by design."""
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", _fake_perfect_llm())
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    big = " ".join(
        f"This is sentence number {i} of an extremely long paragraph that "
        f"keeps going on and on with plenty of words inside it."
        for i in range(12)
    )
    source = [
        "Introduction paragraph with enough words to stand alone as a chunk.",
        big,
        "Tail paragraph A after the big one.",
    ]
    out, stats, logs = await _run(source, max_tokens=60)

    segments = plain_pipeline.build_plain_segments(source, 60)
    assert any(segment['partial'] for segment in segments), (
        "the fixture must actually produce partial segments"
    )
    assert len(out) == len(source)
    assert stats.paragraph_count_mismatches == 0
    assert _mismatch_logs(logs) == []


# ---------------------------------------------------------------------------
# The output marker
# ---------------------------------------------------------------------------
def test_untranslated_block_is_marked():
    """A slot whose translation came back empty falls back to source, marked.

    This is the whole-chunk fallback path (a failed chunk keeps its source
    text). The marker keys on output-text-is-source-text, so it covers both
    this empty slot and the non-empty source text a failed per-paragraph
    repair writes into its own slot.
    """
    body = etree.fromstring(
        "<body>" + "".join(f"<p>{p}</p>" for p in MERGED) + "</body>"
    )
    paragraphs, tags, images = extract_plain_paragraphs(body)

    replace_body_with_paragraphs(
        body, ["T::Alpha paragraph. Beta paragraph.", ""], tags, images,
        source_paragraphs=paragraphs,
    )

    blocks = [(child.get("class"), child.text) for child in body]
    assert blocks == [
        (None, "T::Alpha paragraph. Beta paragraph."),
        ("plain-text-untranslated", "Beta paragraph."),
    ]


def test_translated_blocks_keep_their_classes():
    """Only the source-carrying block is marked; bilingual mode is unchanged."""
    body = etree.fromstring("<body><p>Source one.</p><p>Source two.</p></body>")
    paragraphs, tags, images = extract_plain_paragraphs(body)
    replace_body_with_paragraphs(
        body, ["Traduction une.", ""], tags, images,
        bilingual=True, source_paragraphs=paragraphs,
    )

    classes = [child.get("class") for child in body]
    # Bilingual keeps source/target twins; the empty translation emits no target
    # block at all, since the plain-text-source twin above already carries the
    # text (a block never carries two classes).
    assert classes == ["plain-text-source", "plain-text-target", "plain-text-source"]


# ---------------------------------------------------------------------------
# The deterministic repair
# ---------------------------------------------------------------------------
THREE = ["First one.", "Second one.", "Third one."]

# Groups the source below into three segments of three paragraphs each.
CHECKPOINT_SOURCE = [f"Short paragraph number {i} here." for i in range(9)]
CHECKPOINT_TOKENS = 24


def _big_paragraph():
    return " ".join(
        f"This is sentence number {i} of an extremely long paragraph that "
        f"keeps going on and on with plenty of words inside it."
        for i in range(12)
    )


@pytest.mark.asyncio
async def test_merged_segment_is_repaired_paragraph_by_paragraph(monkeypatch):
    """The merged segment is re-translated one call per paragraph, in place."""
    fake = _recording_merging_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    body = etree.fromstring(
        "<body>" + "".join(f"<p>{p}</p>" for p in THREE) + "</body>"
    )
    paragraphs, tags, images = extract_plain_paragraphs(body)

    out, stats, logs = await _run(paragraphs)

    assert out == ["T::First one.", "T::Second one.", "T::Third one."]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    assert _repair_failure_logs(logs) == []

    # One segment call, then exactly one call per paragraph: 1 + 3.
    assert [call['main'] for call in fake.calls] == ["\n\n".join(THREE)] + THREE
    # Each repair call is positioned by its neighbours inside the segment; the
    # segment's own (empty) context fills the two edges.
    assert [(call['before'], call['after']) for call in fake.calls[1:]] == [
        ("", THREE[1]),
        (THREE[0], THREE[2]),
        (THREE[1], ""),
    ]

    replace_body_with_paragraphs(body, out, tags, images, source_paragraphs=paragraphs)
    assert [child.get("class") for child in body] == [None, None, None]


@pytest.mark.asyncio
async def test_repair_failure_falls_back_to_source_and_is_counted(monkeypatch):
    """A repair call the LLM cannot answer keeps source text, loudly."""
    fake = _recording_merging_llm(fail_on={THREE[1]})
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    body = etree.fromstring(
        "<body>" + "".join(f"<p>{p}</p>" for p in THREE) + "</body>"
    )
    paragraphs, tags, images = extract_plain_paragraphs(body)

    out, stats, logs = await _run(paragraphs)

    assert out == ["T::First one.", "Second one.", "T::Third one."]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 1
    assert len(_repair_failure_logs(logs)) == 1

    # The failed paragraph keeps its source text in its own slot, so the
    # surrounding paragraphs stay aligned, and the extractor marks that block
    # because its output text is its source text. This is the only remaining
    # path that can put source text in the output, and it is loud on all three
    # channels: the counter, the log, and the marker.
    replace_body_with_paragraphs(body, out, tags, images, source_paragraphs=paragraphs)
    assert [(child.get("class"), child.text) for child in body] == [
        (None, "T::First one."),
        ("plain-text-untranslated", "Second one."),
        (None, "T::Third one."),
    ]


@pytest.mark.asyncio
async def test_repair_is_attempted_only_once(monkeypatch):
    """A repair answer that is itself two paragraphs collapses, never recurses."""
    fake = _fake_always_splitting_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    out, stats, logs = await _run(THREE)

    assert out == [f"T::{p} EXTRA" for p in THREE]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    # Still 1 + 3: the surplus paragraph of each repair answer is folded back
    # into its single slot rather than triggering a second repair round.
    assert len(fake.calls) == 4


@pytest.mark.asyncio
async def test_single_paragraph_split_is_benign_and_not_repaired(monkeypatch):
    """A split inside a one-paragraph segment merges back on its own (D4)."""
    fake = _fake_always_splitting_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    out, stats, logs = await _run(["Solo paragraph."])

    assert out == ["T::Solo paragraph. EXTRA"]
    # Counted like any other mismatch, but no warning and no LLM call spent:
    # _reconcile_paragraph_counts already puts the surplus back where it belongs.
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    assert _mismatch_logs(logs) == []
    assert len([1 for key, _ in logs if key == "plain_text_paragraph_split_benign"]) == 1
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_repair_result_is_checkpointed(monkeypatch):
    """A pause after a repaired segment resumes into an identical output."""
    from tests.unit.test_plain_text_checkpoint import _HookRecorder

    segments = plain_pipeline.build_plain_segments(CHECKPOINT_SOURCE, CHECKPOINT_TOKENS)
    assert [len(segment['indices']) for segment in segments] == [3, 3, 3]
    expected = [f"T::{p}" for p in CHECKPOINT_SOURCE]

    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    # 1. Uninterrupted reference run.
    monkeypatch.setattr(
        plain_pipeline, "generate_translation_request", _recording_merging_llm()
    )
    reference, _, _ = await _run(CHECKPOINT_SOURCE, max_tokens=CHECKPOINT_TOKENS)
    assert reference == expected

    # 2. Same run, paused once the first segment has been repaired (1 + 3 calls).
    fake = _recording_merging_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    hook = _HookRecorder()
    _, _, interrupted = await plain_pipeline.translate_paragraphs_plain(
        paragraphs=CHECKPOINT_SOURCE,
        source_language="English",
        target_language="French",
        model_name="m",
        llm_client=object(),
        max_tokens_per_chunk=CHECKPOINT_TOKENS,
        parallel_workers=1,
        checkpoint_hook=hook,
        checkpoint_every=1,
        check_interruption_callback=lambda: len(fake.calls) >= 4,
    )

    assert interrupted is True
    assert hook.last['next_index'] >= 1
    # The persisted prefix carries the repaired text as ONE joined string, which
    # is what keeps the checkpoint format unchanged.
    assert hook.last['prefix'][0] == "\n\n".join(expected[:3])

    # 3. Resuming from that checkpoint reproduces the uninterrupted output.
    resumed, _, _ = await _run(
        CHECKPOINT_SOURCE,
        max_tokens=CHECKPOINT_TOKENS,
        resume_segments=hook.last['segments'],
        resume_translated=hook.last['prefix'],
    )
    assert resumed == reference


@pytest.mark.asyncio
async def test_partial_segment_is_never_repaired(monkeypatch):
    """Pieces of an oversized paragraph have no count contract."""
    fake = _fake_always_splitting_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    source = [_big_paragraph()]
    segments = plain_pipeline.build_plain_segments(source, 60)
    assert len(segments) > 1 and all(segment['partial'] for segment in segments)

    out, stats, logs = await _run(source, max_tokens=60)

    assert len(out) == 1
    assert stats.paragraph_count_mismatches == 0
    assert stats.paragraph_repair_failed == 0
    assert _mismatch_logs(logs) == [] and _repair_failure_logs(logs) == []
    # No per-paragraph call was added on top of the piece calls.
    assert len(fake.calls) == len(segments)


@pytest.mark.asyncio
async def test_oversized_and_merged_combined(monkeypatch):
    """An oversized paragraph and a merged segment in the same file."""
    fake = _recording_merging_llm()
    monkeypatch.setattr(plain_pipeline, "generate_translation_request", fake)
    monkeypatch.setattr(plain_pipeline, "clean_translated_text", lambda s: s)

    source = [
        "Intro paragraph with enough words to stand alone as a chunk.",
        _big_paragraph(),
        "Tail A.", "Tail B.", "Tail C.",
    ]
    segments = plain_pipeline.build_plain_segments(source, 60)
    assert any(segment['partial'] for segment in segments)
    assert segments[-1]['indices'] == [2, 3, 4]

    out, stats, logs = await _run(source, max_tokens=60)

    assert out[0] == f"T::{source[0]}"
    # The oversized paragraph stays in its own slot...
    assert "sentence number" in out[1] and "Tail" not in out[1]
    # ...and the merged tail segment is realigned one paragraph per slot.
    assert out[2:] == ["T::Tail A.", "T::Tail B.", "T::Tail C."]
    assert stats.paragraph_count_mismatches == 1
    assert stats.paragraph_repair_failed == 0
    assert len(fake.calls) == len(segments) + 3


# ---------------------------------------------------------------------------
# The counters
# ---------------------------------------------------------------------------
def test_metrics_roundtrip_and_merge():
    metrics = TranslationMetrics()
    assert metrics.paragraph_count_mismatches == 0
    assert metrics.paragraph_repair_failed == 0

    metrics.paragraph_count_mismatches = 3
    metrics.paragraph_repair_failed = 1

    restored = TranslationMetrics.from_dict(metrics.to_dict())
    assert restored.paragraph_count_mismatches == 3
    assert restored.paragraph_repair_failed == 1

    other = TranslationMetrics()
    other.paragraph_count_mismatches = 4
    other.paragraph_repair_failed = 2
    metrics.merge(other)
    assert metrics.paragraph_count_mismatches == 7
    assert metrics.paragraph_repair_failed == 3
