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
        prompt_options={"enable_refinement": True},
    )

    assert result == ["already translated"]


@pytest.mark.asyncio
async def test_epub_refine_does_not_remap_local_source_placeholders(monkeypatch):
    captured = {}

    def fake_prompt(**kwargs):
        captured.update(kwargs)

        class Pair:
            system = "sys"
            user = "user"

        return Pair()

    monkeypatch.setattr(
        "src.prompts.prompts.generate_post_processing_prompt", fake_prompt
    )

    class FakeClient:
        async def make_request(self, *args, **kwargs):
            class Response:
                content = ""
                prompt_tokens = 0
                completion_tokens = 0
                context_used = 0
                context_limit = 0

            return Response()

    chunk = {
        "text": "[0]Hello[1]",
        "local_tag_map": {"[0]": "<p>", "[1]": "</p>"},
        "global_indices": [1, 2],
    }
    await xhtml_translator._refine_epub_chunks_once(
        translated_chunks=["[1]Bonjour[2]"],
        chunks=[chunk],
        target_language="French",
        model_name="test-model",
        llm_client=FakeClient(),
        context_manager=None,
        placeholder_format=("[", "]"),
        log_callback=None,
        prompt_options={},
        source_chunks=[chunk],
    )

    assert captured["source_translation"] == "[0]Hello[1]"
    assert captured["translated_text"] == "[0]Bonjour[1]"


@pytest.mark.asyncio
async def test_epub_refine_injects_glossary_from_source(monkeypatch):
    captured = {}

    def fake_prompt(**kwargs):
        captured.update(kwargs)

        class Pair:
            system = "sys"
            user = "user"

        return Pair()

    monkeypatch.setattr(
        "src.prompts.prompts.generate_post_processing_prompt", fake_prompt
    )

    class FakeClient:
        async def make_request(self, *args, **kwargs):
            class Response:
                content = ""
                prompt_tokens = 0
                completion_tokens = 0
                context_used = 0
                context_limit = 0

            return Response()

    chunk = {
        "text": "[0]Hello[1]",
        "local_tag_map": {"[0]": "<p>", "[1]": "</p>"},
        "global_indices": [1, 2],
    }
    source_chunk = {
        "text": "[0]The Muggle waved[1]",
        "local_tag_map": {"[0]": "<p>", "[1]": "</p>"},
        "global_indices": [1, 2],
    }
    await xhtml_translator._refine_epub_chunks_once(
        translated_chunks=["[1]Le visiteur salua[2]"],
        chunks=[chunk],
        target_language="French",
        model_name="test-model",
        llm_client=FakeClient(),
        context_manager=None,
        placeholder_format=("[", "]"),
        log_callback=None,
        prompt_options={"glossary_terms": {"Muggle": "Moldu"}},
        source_chunks=[source_chunk],
    )

    assert "Muggle -> Moldu" in (captured.get("glossary_block") or "")


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
    result = await translator.refine_chunks(
        translated_chunks=[draft],
        original_chunks=[{"source_text": "source"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        llm_provider="openai",
        auto_adjust_context=False,
    )

    assert result == [draft]


def test_text_has_placeholders_matches_structure_signature():
    from src.core.refine.structure import text_has_placeholders

    assert text_has_placeholders("Keep [0] and [[id1]]")
    assert text_has_placeholders("token __TEMP_TAG0__ here")
    assert not text_has_placeholders("No markers in this draft.")


@pytest.mark.asyncio
async def test_txt_refine_enables_placeholder_instructions_when_draft_has_them(monkeypatch):
    captured = {}
    original = translator.generate_refinement_prompt

    def spy(*args, **kwargs):
        captured["has_placeholders"] = kwargs.get("has_placeholders")
        return original(*args, **kwargs)

    monkeypatch.setattr(translator, "generate_refinement_prompt", spy)

    from unittest.mock import AsyncMock, Mock
    from src.core.llm.base import LLMResponse

    llm = Mock()
    llm.make_request = AsyncMock(return_value=LLMResponse(
        content="<TRANSLATION>Keep [0]</TRANSLATION>",
        prompt_tokens=1,
        completion_tokens=1,
        context_used=1,
        context_limit=2048,
        was_truncated=False,
    ))
    llm.extract_translation = Mock(return_value="Keep [0]")

    await translator._make_refinement_request(
        draft_translation="Keep [0] exactly.",
        context_before="",
        context_after="",
        previous_refined_context="",
        target_language="French",
        model="test-model",
        llm_client=llm,
        log_callback=None,
        has_placeholders=False,
        prompt_options={},
    )

    assert captured["has_placeholders"] is True
