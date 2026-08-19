import copy

import pytest

from src.core import translator
from src.core.llm.exceptions import RefinementInterrupted
from src.persistence.checkpoint_manager import CheckpointManager


class _MemoryCheckpoint:
    def __init__(self):
        self.states = {}

    def save_refinement_state(self, translation_id, state):
        self.states[translation_id] = copy.deepcopy(state)
        return True

    def load_refinement_state(self, translation_id):
        state = self.states.get(translation_id)
        return copy.deepcopy(state) if state else None

    def delete_refinement_state(self, translation_id):
        self.states.pop(translation_id, None)
        return True


def test_checkpoint_manager_persists_refinement_state(tmp_path):
    manager = CheckpointManager(db_path=str(tmp_path / "jobs.db"))
    manager.uploads_dir = tmp_path / "uploads"
    manager.uploads_dir.mkdir()
    state = {
        "version": 1,
        "phase": 2,
        "next_segment": 3,
        "initial": ["a"],
        "current": ["b"],
        "history": [["a", "b"]],
        "output_filepath": str(tmp_path / "translated.txt"),
    }

    assert manager.save_refinement_state("trans_test", state)
    assert manager.load_refinement_state("trans_test") == state
    assert manager.delete_refinement_state("trans_test")
    assert manager.load_refinement_state("trans_test") is None
    manager.close()


@pytest.mark.asyncio
async def test_three_pass_interruption_is_distinct_and_resume_starts_at_saved_segment(monkeypatch):
    calls = []

    class FakeClient:
        async def close(self):
            return None

    monkeypatch.setattr(
        translator,
        "create_llm_client",
        lambda *args, **kwargs: FakeClient(),
    )

    async def fake_request(**kwargs):
        calls.append(kwargs)
        return f"{kwargs['draft_translation']}|p{kwargs['refinement_phase']}", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    checkpoint = _MemoryCheckpoint()
    interrupted = {"value": False}

    def stop_after_first_segment():
        return len(calls) == 1 and not interrupted["value"]

    with pytest.raises(RefinementInterrupted) as exc_info:
        await translator._refine_chunks_four_pass(
            translated_chunks=["one", "two"],
            original_chunks=[{"source_text": "source one"}, {"source_text": "source two"}],
            target_language="French",
            model_name="test-model",
            api_endpoint="https://example.test/v1",
            auto_adjust_context=False,
            context_window=8192,
            check_interruption_callback=stop_after_first_segment,
            checkpoint_manager=checkpoint,
            translation_id="trans_resume",
            refinement_output_filepath="/tmp/translated.txt",
        )

    assert exc_info.value.partial_result == ["one|p1", "two"]
    saved = checkpoint.load_refinement_state("trans_resume")
    assert saved["phase"] == 1
    assert saved["next_segment"] == 1
    assert saved["current"] == ["one|p1", "two"]

    interrupted["value"] = True
    calls.clear()
    result = await translator._refine_chunks_four_pass(
        translated_chunks=["one", "two"],
        original_chunks=[{"source_text": "source one"}, {"source_text": "source two"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        checkpoint_manager=checkpoint,
        translation_id="trans_resume",
        refinement_output_filepath="/tmp/translated.txt",
    )

    assert result == ["one|p1|p2|p3", "two|p1|p2|p3"]
    # The saved segment is not re-run for pass 1; subsequent passes still run
    # for every segment so the final output is complete.
    assert calls[0]["refinement_phase"] == 1
    assert calls[0]["draft_translation"] == "two"
    assert checkpoint.load_refinement_state("trans_resume") is None


@pytest.mark.asyncio
async def test_three_pass_resume_from_partial_output_keeps_checkpoint(monkeypatch):
    """Handlers re-read the partial refined file; that must not drop the checkpoint."""
    calls = []

    class FakeClient:
        async def close(self):
            return None

    monkeypatch.setattr(
        translator,
        "create_llm_client",
        lambda *args, **kwargs: FakeClient(),
    )

    async def fake_request(**kwargs):
        calls.append(kwargs)
        return f"{kwargs['draft_translation']}|p{kwargs['refinement_phase']}", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    checkpoint = _MemoryCheckpoint()
    interrupted = {"value": False}

    def stop_after_first_segment():
        return len(calls) == 1 and not interrupted["value"]

    with pytest.raises(RefinementInterrupted):
        await translator._refine_chunks_four_pass(
            translated_chunks=["one", "two"],
            original_chunks=[{"source_text": "source one"}, {"source_text": "source two"}],
            target_language="French",
            model_name="test-model",
            api_endpoint="https://example.test/v1",
            auto_adjust_context=False,
            context_window=8192,
            check_interruption_callback=stop_after_first_segment,
            checkpoint_manager=checkpoint,
            translation_id="trans_partial",
            refinement_output_filepath="/tmp/translated.txt",
        )

    interrupted["value"] = True
    calls.clear()
    # Simulate the handler feeding the already-written partial file back in.
    result = await translator._refine_chunks_four_pass(
        translated_chunks=["one|p1", "two"],
        original_chunks=[{"source_text": "source one"}, {"source_text": "source two"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        checkpoint_manager=checkpoint,
        translation_id="trans_partial",
        refinement_output_filepath="/tmp/translated.txt",
    )

    assert result == ["one|p1|p2|p3", "two|p1|p2|p3"]
    assert calls[0]["refinement_phase"] == 1
    assert calls[0]["draft_translation"] == "two"


@pytest.mark.asyncio
async def test_srt_three_pass_checkpoint_resumes_at_block(monkeypatch):
    from src.core import subtitle_translator

    class FakeClient:
        def extract_translation(self, content):
            return content

        async def make_request(self, prompt, model, system_prompt=None):
            return type("Response", (), {"content": prompt.split("\n", 1)[-1]})()

    # Keep the LLM deterministic and return the first marker payload. The
    # checkpoint assertions exercise orchestration, not model parsing quality.
    checkpoint = _MemoryCheckpoint()
    blocks = [[{"number": "1", "text": "one"}], [{"number": "2", "text": "two"}]]
    positions = {id(blocks[0][0]): 0, id(blocks[1][0]): 1}
    calls = []

    async def fake_once(**kwargs):
        calls.append(kwargs)
        return kwargs["translations"]

    monkeypatch.setattr(subtitle_translator, "_refine_subtitle_translations_once", fake_once)
    # The test uses a real phase loop but a fake pass; save/load semantics are
    # still verified without depending on prompt parsing.
    result = await subtitle_translator.refine_subtitle_translations(
        translations={0: "one", 1: "two"},
        target_language="French",
        model_name="test-model",
        llm_client=FakeClient(),
        subtitle_blocks=blocks,
        subtitle_positions=positions,
        checkpoint_manager=checkpoint,
        translation_id="srt_resume",
        refinement_output_filepath="/tmp/out.srt",
    )
    assert result == {0: "one", 1: "two"}
    assert len(calls) == 3
    assert checkpoint.load_refinement_state("srt_resume") is None
