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
        "phase": 1,
        "next_segment": 3,
        "current": ["a", "b"],
        "output_filepath": str(tmp_path / "translated.txt"),
    }

    assert manager.save_refinement_state("trans_test", state)
    assert manager.load_refinement_state("trans_test") == state
    assert manager.delete_refinement_state("trans_test")
    assert manager.load_refinement_state("trans_test") is None
    manager.close()


@pytest.mark.asyncio
async def test_one_pass_interruption_saves_and_resume_starts_at_saved_segment(monkeypatch):
    calls = []

    class FakeClient:
        async def close(self):
            return None

        async def detect_thinking_model(self):
            return None

    monkeypatch.setattr(
        translator,
        "create_llm_client",
        lambda *args, **kwargs: FakeClient(),
    )

    async def fake_request(**kwargs):
        calls.append(kwargs["draft_translation"])
        return f"{kwargs['draft_translation']}|refined", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    checkpoint = _MemoryCheckpoint()
    interrupted = {"value": False}

    def stop_after_first_segment():
        return len(calls) == 1 and not interrupted["value"]

    with pytest.raises(RefinementInterrupted) as exc_info:
        await translator.refine_chunks(
            translated_chunks=["one", "two"],
            original_chunks=[{}, {}],
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

    assert exc_info.value.partial_result == ["one|refined", "two"]
    saved = checkpoint.load_refinement_state("trans_resume")
    assert saved["phase"] == 1
    assert saved["next_segment"] == 1
    assert saved["current"] == ["one|refined", "two"]
    assert saved["output_filepath"] == "/tmp/translated.txt"

    interrupted["value"] = True
    calls.clear()
    result = await translator.refine_chunks(
        translated_chunks=["one", "two"],
        original_chunks=[{}, {}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        checkpoint_manager=checkpoint,
        translation_id="trans_resume",
        refinement_output_filepath="/tmp/translated.txt",
    )

    assert result == ["one|refined", "two|refined"]
    assert calls == ["two"]
    assert checkpoint.load_refinement_state("trans_resume") is None


@pytest.mark.asyncio
async def test_one_pass_resume_from_partial_output_keeps_checkpoint(monkeypatch):
    calls = []

    class FakeClient:
        async def close(self):
            return None

        async def detect_thinking_model(self):
            return None

    monkeypatch.setattr(
        translator,
        "create_llm_client",
        lambda *args, **kwargs: FakeClient(),
    )

    async def fake_request(**kwargs):
        calls.append(kwargs["draft_translation"])
        return f"{kwargs['draft_translation']}|refined", object()

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    checkpoint = _MemoryCheckpoint()
    interrupted = {"value": False}

    def stop_after_first_segment():
        return len(calls) == 1 and not interrupted["value"]

    with pytest.raises(RefinementInterrupted):
        await translator.refine_chunks(
            translated_chunks=["one", "two"],
            original_chunks=[{}, {}],
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
    result = await translator.refine_chunks(
        translated_chunks=["one|refined", "two"],
        original_chunks=[{}, {}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        checkpoint_manager=checkpoint,
        translation_id="trans_partial",
        refinement_output_filepath="/tmp/translated.txt",
    )

    assert result == ["one|refined", "two|refined"]
    assert calls == ["two"]


@pytest.mark.asyncio
async def test_srt_one_pass_checkpoint_resumes_at_block(monkeypatch):
    from src.core import subtitle_translator

    checkpoint = _MemoryCheckpoint()
    calls = []

    async def fake_once(**kwargs):
        calls.append(kwargs["start_block_index"])
        if kwargs["start_block_index"] == 0:
            from src.core.llm.exceptions import RefinementInterrupted
            exc = RefinementInterrupted(partial_result={0: "one-partial", 1: "two"})
            exc.refinement_index = 1
            raise exc
        return {0: "one-partial", 1: "two-refined"}

    monkeypatch.setattr(subtitle_translator, "_refine_subtitle_translations_once", fake_once)

    with pytest.raises(RefinementInterrupted) as exc_info:
        await subtitle_translator.refine_subtitle_translations(
            translations={0: "one", 1: "two"},
            target_language="French",
            model_name="test-model",
            llm_client=object(),
            checkpoint_manager=checkpoint,
            translation_id="srt_resume",
            refinement_output_filepath="/tmp/out.srt",
        )

    assert exc_info.value.refinement_state["current"][0] == "one-partial"
    saved = checkpoint.load_refinement_state("srt_resume")
    assert saved["next_segment"] == 1

    result = await subtitle_translator.refine_subtitle_translations(
        translations={0: "one", 1: "two"},
        target_language="French",
        model_name="test-model",
        llm_client=object(),
        checkpoint_manager=checkpoint,
        translation_id="srt_resume",
        refinement_output_filepath="/tmp/out.srt",
    )
    assert result == {0: "one-partial", 1: "two-refined"}
    assert calls == [0, 1]
    assert checkpoint.load_refinement_state("srt_resume") is None
