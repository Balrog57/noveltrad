import pytest

from src.core.epub import xhtml_translator
from src.core.refine.structure import is_plain_text_structure_safe
from src.core import translator


@pytest.mark.asyncio
async def test_epub_refinement_keeps_previous_chunks_on_alignment_mismatch():
    result = await xhtml_translator._refine_epub_chunks_once(
        translated_chunks=["already translated"],
        chunks=[],
        target_language="French",
        model_name="test-model",
        llm_client=object(),
        context_manager=None,
        placeholder_format=("[", "]"),
        log_callback=None,
        prompt_options={"refinement_phase": 1},
    )

    assert result == ["already translated"]


def test_plain_text_structure_guard_rejects_markdown_drift():
    original = "# Chapter\n\n- Keep this [link](https://example.test).\n\n```python\nprint(1)\n```"
    changed = "# Chapter\n\nKeep this link."

    assert is_plain_text_structure_safe(original, original)
    assert not is_plain_text_structure_safe(original, changed)


@pytest.mark.asyncio
async def test_generic_refinement_keeps_draft_when_structure_changes(monkeypatch):
    class FakeClient:
        async def close(self):
            return None

    monkeypatch.setattr(translator, "create_llm_client", lambda *args, **kwargs: FakeClient())

    async def fake_request(**kwargs):
        return "# Chapter\n\nchanged", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    draft = "# Chapter\n\n- Keep this [link](https://example.test)."
    result = await translator._refine_chunks_four_pass(
        translated_chunks=[draft],
        original_chunks=[{"source_text": "source"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
    )

    assert result == [draft]
