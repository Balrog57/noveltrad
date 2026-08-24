"""Integration tests for retrying failed EPUB chunks on resume (issue #261).

A job that ends `partial` because one chunk fell back to its source text used to
be unfinishable: the resume pointer is a file index, so the file holding the bad
chunk counted as done and Resume translated nothing. These tests pin the fix end
to end, on a 3-chapter in-memory EPUB and with no network at all
(`generate_translation_request` is stubbed inside the xhtml_translator module).

Three scenarios, in order:

1. Pass 1 starves chapter 2's only chunk: the verdict is `partial`, the job
   progress lists the unfinished chunk under `epub_unfinished_units`, and the
   per-file partial state of chapter 2 - and only chapter 2 - survives (which
   also pins the state-key unification: chapters 1 and 3 are cleaned up).
2. Pass 2 with the starvation lifted retries exactly that one chunk, nothing
   else, and the job comes back clean: no ticket, no partial state, chapter 2
   translated in the output EPUB.
3. Pass 2 with the starvation still in place retries exactly once, stays
   `partial` and keeps its ticket - no false success, no retry loop.
"""

import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.core.epub.translator as epub_translator
import src.core.epub.xhtml_translator as xhtml_translator
from src.api.completion_status import classify_completion
from src.persistence.checkpoint_manager import CheckpointManager


# The sabotaged chunk is identified by this sentinel: the stub returns None for
# any request containing it, in Phase 1 (with placeholders) and in Phase 2
# (placeholders stripped), which is what pushes the chunk into Phase 3.
SENTINEL = "The keeper refused to name the seventh lamp"

# Marker the stub prepends to a successful "translation". A chapter carrying it
# has been through the LLM; a chapter without it is still source text.
TRANSLATED_MARKER = "[FR]"

MODEL = "test-model"
# Large enough that each short chapter is exactly one chunk.
MAX_TOKENS_PER_CHUNK = 2000

PARAGRAPHS = [
    "The lighthouse keeper's journal had grown thick with salt and ink.",
    "Every evening the lamp was wound and the log signed in the same hand.",
]


# ---------------------------------------------------------------------------
# Fixture: a 3-chapter EPUB whose chapter 2 carries the sentinel
# ---------------------------------------------------------------------------

def _chapter_xhtml(title, paragraphs):
    body = "\n".join("    <p>%s</p>" % p for p in paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n'
        '<head><title>%s</title></head>\n'
        '<body>\n'
        '  <h1>%s</h1>\n'
        '%s\n'
        '</body>\n'
        '</html>\n' % (title, title, body)
    )


def _build_epub(path):
    """3 chapters; chapter 2 carries the paragraph that will fail to translate."""
    hrefs = ["chapter%d.xhtml" % (i + 1) for i in range(3)]
    manifest = "\n".join(
        '    <item id="ch%d" href="%s" media-type="application/xhtml+xml"/>'
        % (i + 1, href) for i, href in enumerate(hrefs)
    )
    spine = "\n".join('    <itemref idref="ch%d"/>' % (i + 1) for i in range(3))
    content_opf = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package version="3.0" xmlns="http://www.idpf.org/2007/opf" '
        'unique-identifier="bookid">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '    <dc:identifier id="bookid">urn:uuid:261</dc:identifier>\n'
        '    <dc:title>The Seventh Lamp</dc:title>\n'
        '    <dc:language>en</dc:language>\n'
        '    <meta property="dcterms:modified">2024-01-01T00:00:00Z</meta>\n'
        '  </metadata>\n'
        '  <manifest>\n' + manifest + '\n  </manifest>\n'
        '  <spine>\n' + spine + '\n  </spine>\n'
        '</package>\n'
    )
    container_xml = (
        '<?xml version="1.0"?>\n'
        '<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    )
    sabotaged = list(PARAGRAPHS)
    sabotaged[1] = SENTINEL + ", and the assistant never asked twice."

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container_xml)
        z.writestr("OEBPS/content.opf", content_opf)
        for i, href in enumerate(hrefs):
            paragraphs = sabotaged if i == 1 else PARAGRAPHS
            z.writestr("OEBPS/" + href,
                       _chapter_xhtml("Chapter %d" % (i + 1), paragraphs))


def _chapter_text(epub_path, href):
    """Read one chapter out of an output EPUB (empty string when absent)."""
    if not Path(epub_path).exists():
        return ""
    with zipfile.ZipFile(epub_path) as z:
        for name in z.namelist():
            if name.endswith(href):
                return z.read(name).decode("utf-8", errors="replace")
    return ""


@pytest.fixture
def epub_job(tmp_path, monkeypatch):
    """An extracted-and-registered EPUB job with an isolated checkpoint store."""
    input_path = tmp_path / "seventh_lamp.epub"
    output_path = tmp_path / "seventh_lamp_fr.epub"
    _build_epub(input_path)

    manager = CheckpointManager(db_path=str(tmp_path / "jobs.db"))
    manager.uploads_dir = tmp_path / "uploads"
    manager.uploads_dir.mkdir(parents=True, exist_ok=True)

    translation_id = "retry261"
    manager.start_job(
        translation_id=translation_id,
        file_type="epub",
        config={
            'file_path': str(input_path),
            'output_filename': output_path.name,
            'source_language': "English",
            'target_language': "French",
            'model': MODEL,
            'llm_provider': "ollama",
            'file_type': "epub",
        },
        input_file_path=str(input_path),
    )

    # No LLM client is ever needed: chunk requests are stubbed per pass and the
    # packaging-metadata pass (the only other LLM caller) is switched off.
    monkeypatch.setattr(epub_translator, "_create_llm_client",
                        lambda **kwargs: MagicMock())
    monkeypatch.setattr(epub_translator, "EPUB_TRANSLATE_METADATA_ENABLED", False)

    return {
        'input': input_path,
        'output': output_path,
        'manager': manager,
        'translation_id': translation_id,
    }


# ---------------------------------------------------------------------------
# One translation pass
# ---------------------------------------------------------------------------

async def _run_pass(job, monkeypatch, resume_from_index, starve,
                    payload_sink=None):
    """Run one EPUB pass and return (stats, chunk_requests, log_kinds).

    `starve` decides whether the sentinel chunk is answered. Every chunk-level
    LLM request is recorded, so a test can assert exactly which chunks were
    translated.

    `payload_sink`, when given, collects every stats payload in emission order.
    The returned `stats` dict is the merge of all of them (which is what the web
    layer keeps), so it can only answer "what did the panel end on"; the sink is
    how a test can look at the *first* emit of a pass.
    """
    requests = []
    log_kinds = []

    async def fake_generate_translation_request(main_content, *args, **kwargs):
        requests.append(main_content)
        if starve and SENTINEL in main_content:
            return None
        return "%s %s" % (TRANSLATED_MARKER, main_content)

    monkeypatch.setattr(xhtml_translator, "generate_translation_request",
                        fake_generate_translation_request)

    stats = {}

    def stats_callback(payload):
        if payload_sink is not None:
            payload_sink.append(dict(payload))
        stats.update(payload)

    def log_callback(kind, message, **kwargs):
        log_kinds.append(kind)

    await epub_translator.translate_epub_file(
        input_filepath=str(job['input']),
        output_filepath=str(job['output']),
        source_language="English",
        target_language="French",
        model_name=MODEL,
        llm_provider="ollama",
        checkpoint_manager=job['manager'],
        translation_id=job['translation_id'],
        resume_from_index=resume_from_index,
        log_callback=log_callback,
        stats_callback=stats_callback,
        max_tokens_per_chunk=MAX_TOKENS_PER_CHUNK,
        max_attempts=1,
        prompt_options={},
    )

    return stats, requests, log_kinds


def _job_progress(job):
    return job['manager'].get_job(job['translation_id'])['progress']


def _sentinel_requests(requests):
    return [text for text in requests if SENTINEL in text]


async def _first_pass(job, monkeypatch):
    """Pass 1: chapter 2's chunk is starved and ends up as source text."""
    stats, requests, _kinds = await _run_pass(
        job, monkeypatch, resume_from_index=0, starve=True)

    verdict = classify_completion(stats, str(job['output']))
    assert verdict.status == 'partial'
    assert verdict.fallback_chunks == 1

    # A fresh pass restores nothing, so the per-run counters (emitted
    # unconditionally, never only-sometimes) equal the accumulated ones.
    assert stats['run_processed_chunks'] == stats['processed_chunks'] == 3
    assert stats['run_fallback_used'] == stats['fallback_used'] == 1

    # Live count of chunks currently sitting in their source text. Unlike
    # `fallback_used` (accumulated across passes) this one is a projection of
    # the per-chunk statuses, which is what lets the Fallbacks stat card count
    # down when a retry heals a chunk.
    assert stats['untranslated_chunks'] == 1

    # Mirror what handlers.py does with a partial job: keep the checkpoint.
    job['manager'].mark_partial(job['translation_id'])
    return stats, requests


# ---------------------------------------------------------------------------
# 1 + 2. The fallback chunk is recorded, then retried and healed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_retries_only_the_unfinished_chunk(epub_job, monkeypatch):
    manager = epub_job['manager']
    translation_id = epub_job['translation_id']

    # === PASS 1: chapter 2 starves ===
    await _first_pass(epub_job, monkeypatch)

    progress = _job_progress(epub_job)
    assert progress['epub_unfinished_units'] == {'chapter2.xhtml': [0]}
    # Only the file with unfinished work keeps its partial state; the two clean
    # chapters were deleted after being saved (state-key unification).
    assert manager.list_xhtml_partial_states(translation_id) == ['chapter2.xhtml']
    # The file pointer still says "all three files done".
    assert manager.load_checkpoint(translation_id)['resume_from_index'] == 3
    assert TRANSLATED_MARKER not in _chapter_text(epub_job['output'],
                                                  "chapter2.xhtml")

    # === PASS 2: resume with the starvation lifted ===
    resume_from_index = manager.load_checkpoint(translation_id)['resume_from_index']
    _stats2, requests2, kinds2 = await _run_pass(
        epub_job, monkeypatch, resume_from_index=resume_from_index, starve=False)

    # Exactly one chunk was translated, and it is the sabotaged one.
    assert len(requests2) == 1
    assert SENTINEL in requests2[0]
    assert 'epub_retry_file' in kinds2
    assert 'epub_retry_state_missing' not in kinds2

    assert TRANSLATED_MARKER in _chapter_text(epub_job['output'],
                                              "chapter2.xhtml")

    # Chunk accounting: the re-entered file must be counted once, not twice
    # (it is excluded from the pre-loop sum and added back after processing).
    assert _stats2['completed_chunks'] == _stats2['total_chunks'] == 3

    # Per-run counters. The accumulated ones are rehydrated across passes on
    # purpose (issue #180: the Fallbacks card must not reset to zero), which
    # makes any percentage derived from them a cross-pass average - and worse,
    # a re-entered file replays its own restored metrics on top of the snapshot
    # that already counted them (processed_chunks: 3 restored + 1 replayed + 1
    # new = 5 for a 3-chunk book, fallback_used: 1 counted twice). The `run_*`
    # twins are what the completion card divides by, and they describe exactly
    # this pass: one chunk retried, cleanly.
    assert _stats2['run_processed_chunks'] == 1
    assert _stats2['run_fallback_used'] == 0
    assert _stats2['run_token_alignment_used'] == 0
    assert _stats2['run_successful_after_retry'] == 0
    assert _stats2['run_placeholder_errors'] == 0
    assert _stats2['processed_chunks'] == 5
    assert _stats2['fallback_used'] == 2

    # The live Fallbacks card counts down as the retry heals the chunk: the
    # accumulated counter still remembers both fallbacks (issue #180 - it must
    # not reset on resume), while `untranslated_chunks` describes the book as it
    # now stands, and nothing is in the source language any more.
    assert _stats2['untranslated_chunks'] == 0

    # Nothing is owed any more: no ticket, no partial state left.
    assert _job_progress(epub_job)['epub_unfinished_units'] == {}
    assert manager.list_xhtml_partial_states(translation_id) == []
    assert manager.load_xhtml_partial_state(translation_id,
                                            "chapter2.xhtml") is None

    # The resume pointer must not have rewound to the re-entered file: it stays
    # at "all files done", so a further resume cannot re-enter files 1 and 3
    # without a partial state.
    assert manager.load_checkpoint(translation_id)['resume_from_index'] == 3

    # The chapters that were already fine were neither re-translated nor lost.
    for href in ("chapter1.xhtml", "chapter3.xhtml"):
        assert TRANSLATED_MARKER in _chapter_text(epub_job['output'], href)


# ---------------------------------------------------------------------------
# 2b. The live Fallbacks card: hydrated on resume, then counting down
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_untranslated_chunks_is_hydrated_before_the_retry_runs(
        epub_job, monkeypatch):
    """The very first emit of a resumed pass already knows about the fallback.

    This is the issue #180 guard, transposed to the new counter: the Fallbacks
    card must show the damage inherited from the previous pass, not 0, before a
    single chunk of the retry has been translated. The pre-loop emit reads it
    from the per-file partial states the retry tickets are built from - the
    stored `epub_unfinished_units` map merges pending with untranslated and
    could not answer this.
    """
    manager = epub_job['manager']
    translation_id = epub_job['translation_id']

    await _first_pass(epub_job, monkeypatch)
    resume_from_index = manager.load_checkpoint(translation_id)['resume_from_index']

    payloads = []
    stats2, _requests2, _kinds2 = await _run_pass(
        epub_job, monkeypatch, resume_from_index=resume_from_index,
        starve=False, payload_sink=payloads)

    # First emit of the pass: nothing has been retried yet, and the card is
    # already at 1 (the chunk pass 1 left in English), not at 0.
    assert payloads
    assert payloads[0]['untranslated_chunks'] == 1
    # The re-entered file is deliberately excluded from the pre-loop chunk sum
    # (the loop adds it back once processed), so 2 of the 3 chunks are counted:
    # this really is the emit that precedes any retry work.
    assert payloads[0]['completed_chunks'] == 2

    # ... and by the end of the pass the same key has counted down to 0.
    assert payloads[-1]['untranslated_chunks'] == 0
    assert stats2['untranslated_chunks'] == 0
    # The card's other term is unaffected: no chunk ever needed Phase 2 here.
    assert stats2['token_alignment_used'] == 0


# ---------------------------------------------------------------------------
# 3. A retry that fails again: still partial, ticket kept, one attempt only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_retry_that_fails_again_keeps_the_ticket(epub_job, monkeypatch):
    manager = epub_job['manager']
    translation_id = epub_job['translation_id']

    _stats1, requests1 = await _first_pass(epub_job, monkeypatch)
    resume_from_index = manager.load_checkpoint(translation_id)['resume_from_index']

    # === PASS 2': resume with the starvation still in place ===
    stats2, requests2, kinds2 = await _run_pass(
        epub_job, monkeypatch, resume_from_index=resume_from_index, starve=True)

    # The sabotaged chunk walked the same ladder exactly once (Phase 1 with the
    # placeholders, Phase 2 without), and no other chunk was touched.
    assert requests2 == _sentinel_requests(requests1)
    assert len(requests2) >= 1
    assert 'epub_retry_file' in kinds2

    # This pass retried one chunk and it fell back again: 1 of 1, not 3 of 5.
    assert stats2['run_processed_chunks'] == 1
    assert stats2['run_fallback_used'] == 1
    assert stats2['fallback_used'] == 3

    # Still one chunk in the source language, so the card holds at 1 - it does
    # not follow the accumulated counter up to 3.
    assert stats2['untranslated_chunks'] == 1

    verdict2 = classify_completion(stats2, str(epub_job['output']))
    assert verdict2.status == 'partial'

    # The ticket and its payload are still there, so the user can retry again.
    assert _job_progress(epub_job)['epub_unfinished_units'] == {'chapter2.xhtml': [0]}
    assert manager.list_xhtml_partial_states(translation_id) == ['chapter2.xhtml']
    state = manager.load_xhtml_partial_state(translation_id, "chapter2.xhtml")
    assert state is not None
    assert state.validate() is True
    assert SENTINEL in state.translated_chunks[0]
    assert manager.load_checkpoint(translation_id)['resume_from_index'] == 3
    assert TRANSLATED_MARKER not in _chapter_text(epub_job['output'],
                                                 "chapter2.xhtml")
