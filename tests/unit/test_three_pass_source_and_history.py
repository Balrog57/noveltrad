import pytest

from src.core import translator
from src.prompts.prompts import generate_refinement_prompt


@pytest.mark.asyncio
async def test_three_pass_refinement_keeps_source_and_same_segment_history(monkeypatch):
    calls = []

    class FakeClient:
        async def close(self):
            return None

    monkeypatch.setattr(translator, "create_llm_client", lambda *args, **kwargs: FakeClient())

    async def fake_request(**kwargs):
        calls.append(kwargs)
        phase = kwargs["refinement_phase"]
        return f"pass-{phase}", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)

    result = await translator._refine_chunks_four_pass(
        translated_chunks=["initial draft"],
        original_chunks=[{"source_text": "source sentence"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
    )

    assert result == ["pass-3"]
    assert len(calls) == 3
    assert [call["source_translation"] for call in calls] == [
        "source sentence",
        "source sentence",
        "source sentence",
    ]
    assert [call["initial_translation"] for call in calls] == [
        "initial draft",
        "initial draft",
        "initial draft",
    ]
    assert [call["previous_refined_translation"] for call in calls] == [
        "",
        "pass-1",
        "pass-2",
    ]


def test_refinement_prompt_lists_all_same_segment_revisions():
    prompt = generate_refinement_prompt(
        draft_translation="pass 2",
        target_language="French",
        refinement_phase=3,
        source_translation="source sentence",
        initial_translation="initial translation",
        refinement_history=["pass 1", "pass 2"],
    )

    assert "# REFINEMENT HISTORY" in prompt.user
    assert "Revision 1:\npass 1" in prompt.user
    assert "Revision 2:\npass 2" in prompt.user
    assert "source sentence" in prompt.user


@pytest.mark.asyncio
async def test_epub_three_pass_accumulates_same_segment_history(monkeypatch):
    """EPUB/DOCX refine must feed prior revisions into later passes."""
    from src.core.epub import xhtml_translator

    calls = []

    async def fake_once(**kwargs):
        calls.append({
            "phase": kwargs["prompt_options"]["refinement_phase"],
            "histories": kwargs.get("refinement_histories"),
            "drafts": list(kwargs["translated_chunks"]),
        })
        phase = kwargs["prompt_options"]["refinement_phase"]
        return [f"pass-{phase}"]

    monkeypatch.setattr(xhtml_translator, "_refine_epub_chunks_once", fake_once)

    result = await xhtml_translator._refine_epub_chunks(
        translated_chunks=["initial draft"],
        chunks=[{"text": "source sentence", "local_tag_map": {}, "global_indices": []}],
        target_language="French",
        model_name="test-model",
        llm_client=object(),
        context_manager=None,
        placeholder_format=("[id", "]"),
        log_callback=None,
        prompt_options={},
        source_chunks=[{"text": "source sentence"}],
    )

    assert result == ["pass-3"]
    assert [call["phase"] for call in calls] == [1, 2, 3]
    assert calls[0]["histories"] == [[]]
    assert calls[1]["histories"] == [["pass-1"]]
    assert calls[2]["histories"] == [["pass-1", "pass-2"]]
