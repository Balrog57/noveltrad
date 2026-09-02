"""Mocked Refine+ pipeline: call counts, extra cap, JSON publication, resume."""
import json

import pytest

from src.config import TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
from src.core.refine.plus_pipeline import is_refine_plus_enabled, refine_plus_segment
from src.core.refine.refinement_checkpoint import load_plus_state, save_plus_state

GOOD = "Lin met Zhao in the garden in 2012."
SOURCE = "Lin met Zhao in the garden in 2012."
GLOSSARY = {"Lin": "Lin", "Zhao": "Zhao"}
SECRET = "DO_NOT_PUBLISH_NOTES"


def _wrap(inner: str) -> str:
    return f"{TRANSLATE_TAG_IN}\n{inner}\n{TRANSLATE_TAG_OUT}"


def _classify(prompt_pair) -> str:
    text = f"{prompt_pair.system}\n{prompt_pair.user}"
    lowered = text.lower()
    if "qa check for omission" in lowered:
        return "omission"
    if "enforce glossary mappings" in lowered:
        return "pass3"
    if "final proofreading" in lowered:
        return "pass4"
    if "fluency and register" in lowered:
        return "pass2"
    return "pass1"


def _json_body(field: str, text: str) -> str:
    payload = {field: text, "changes": [], "conflicts": [], "edits": [], "notes": SECRET, "omissions": [SECRET]}
    return _wrap(json.dumps(payload))


class _ScriptedLLM:
    def __init__(self, pass1_text=GOOD, pass2_text=GOOD, pass3_text=GOOD, pass4_text=GOOD, extra_text=GOOD):
        self.calls = []
        self.pass1_text = pass1_text
        self.pass2_text = pass2_text
        self.pass3_text = pass3_text
        self.pass4_text = pass4_text
        self.extra_text = extra_text

    async def __call__(self, prompt_pair, *, temperature=None):
        kind = _classify(prompt_pair)
        self.calls.append({"kind": kind, "temperature": temperature})
        if kind == "pass1":
            return _wrap(self.pass1_text)
        if kind == "pass2":
            return _wrap(self.pass2_text)
        if kind == "pass3":
            return _json_body("translation", self.pass3_text)
        if kind == "pass4":
            return _json_body("final", self.pass4_text)
        return _json_body("translation", self.extra_text)


def _options(with_glossary: bool) -> dict:
    opts = {"source_language": "English", "refine_plus": True}
    if with_glossary:
        opts["glossary_terms"] = dict(GLOSSARY)
    return opts


@pytest.mark.asyncio
async def test_four_llm_calls_when_glossary_hits():
    llm = _ScriptedLLM()
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    kinds = [c["kind"] for c in llm.calls]
    assert kinds == ["pass1", "pass2", "pass3", "pass4"]
    assert result.llm_calls == 4
    assert result.skipped_glossary is False
    assert SECRET not in result.text
    assert "2012" in result.text


@pytest.mark.asyncio
async def test_three_llm_calls_when_no_glossary_hits():
    llm = _ScriptedLLM()
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(False),
        llm_generate=llm,
    )
    kinds = [c["kind"] for c in llm.calls]
    assert kinds == ["pass1", "pass2", "pass4"]
    assert result.llm_calls == 3
    assert result.skipped_glossary is True
    assert not any(c["kind"] == "omission" for c in llm.calls)


@pytest.mark.asyncio
async def test_omission_qa_only_when_heuristics_fail_and_extra_at_most_once():
    llm = _ScriptedLLM(pass1_text="Lin met Zhao in the garden.")
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    kinds = [c["kind"] for c in llm.calls]
    assert kinds.count("omission") == 1
    assert kinds[0] == "pass1"
    assert kinds[1] == "omission"
    assert result.extra_used is True
    assert result.llm_calls == 5  # 4 + 1 extra
    assert kinds.count("pass1") == 1
    assert not any(k == "omission" for k in kinds[2:])


@pytest.mark.asyncio
async def test_final_eval_extra_is_capped_at_one():
    llm = _ScriptedLLM(pass4_text="Lin met Zhao in the garden.")
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(False),
        llm_generate=llm,
    )
    kinds = [c["kind"] for c in llm.calls]
    assert kinds.count("omission") + kinds[3:].count("pass1") <= 1
    assert result.extra_used is True
    assert result.llm_calls == 4  # 3 regular + 1 extra, no glossary


@pytest.mark.asyncio
async def test_adaptive_temperatures():
    llm = _ScriptedLLM()
    await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    temps = {c["kind"]: c["temperature"] for c in llm.calls}
    assert temps["pass1"] == 0.2
    assert temps["pass2"] == 0.5
    assert temps["pass3"] == 0.2
    assert temps["pass4"] == 0.2


@pytest.mark.asyncio
async def test_resume_mid_pass_2_skips_pass_1():
    llm = _ScriptedLLM()
    persist = []

    def on_pass(next_pass, text, extra_used):
        persist.append((next_pass, text, extra_used))

    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
        start_pass=2,
        current_text=GOOD,
        extra_used=False,
        on_pass_complete=on_pass,
    )
    kinds = [c["kind"] for c in llm.calls]
    assert "pass1" not in kinds
    assert kinds == ["pass2", "pass3", "pass4"]
    assert persist[0][0] == 3
    assert SECRET not in result.text


def test_plus_checkpoint_roundtrip():
    class _Memory:
        def __init__(self):
            self.states = {}

        def save_refinement_state(self, translation_id, state):
            self.states[translation_id] = dict(state)
            return True

        def load_refinement_state(self, translation_id):
            state = self.states.get(translation_id)
            return dict(state) if state else None

    mem = _Memory()
    save_plus_state(
        mem, "job",
        next_segment=0, total_segments=2, current=["a", "b"],
        pass_index=2, extra_used=False, segment_current="after-pass-1",
        output_filepath="/tmp/out.txt",
        extra={
            "last_qa": {"numbers_ok": True, "glossary_ok": True},
            "decision_log": [{"event": "refine_plus_qa", "message": "accept"}],
        },
    )
    start, current, pass_index, extra_used, segment_current, raw = load_plus_state(
        mem, "job", total_segments=2,
    )
    assert start == 0
    assert current == ["a", "b"]
    assert pass_index == 2
    assert extra_used is False
    assert segment_current == "after-pass-1"
    assert raw["version"] == 2
    assert raw["last_qa"]["numbers_ok"] is True
    assert raw["decision_log"][0]["event"] == "refine_plus_qa"


def test_is_refine_plus_enabled():
    assert is_refine_plus_enabled({"refine_plus": True}) is True
    assert is_refine_plus_enabled({"refine_plus": False}) is False
    assert is_refine_plus_enabled({}) is False
    assert is_refine_plus_enabled(None) is False


def test_cost_estimator_counts_four_plus_passes():
    from src.core.pricing.estimator import CostEstimator

    estimator = CostEstimator("openai", "gpt-4o-mini", {"input": 1.0, "output": 1.0})
    text = "Once upon a time there was a garden. " * 40
    plus_only = estimator.estimate(text, "English", "French", {"refine_plus": True, "refine_only": True})
    plus_after = estimator.estimate(text, "English", "French", {"refine_plus": True})
    one_pass = estimator.estimate(text, "English", "French", {"refine": True})
    assert plus_only["passes"] == 4
    assert plus_after["passes"] == 5
    assert one_pass["passes"] == 2


@pytest.mark.asyncio
async def test_refine_chunks_plus_bypasses_one_pass_ape(monkeypatch):
    from src.core import translator
    from src.core.refine.plus_pipeline import PlusPassResult

    one_pass = []

    class FakeClient:
        async def close(self):
            return None

        async def detect_thinking_model(self):
            return None

    monkeypatch.setattr(translator, "create_llm_client", lambda *args, **kwargs: FakeClient())

    async def fake_request(**kwargs):
        one_pass.append(kwargs)
        return f"{kwargs['draft_translation']}|one-pass", object()

    async def fake_plus(**kwargs):
        return PlusPassResult(text=f"{kwargs['draft']}|plus", llm_calls=4)

    monkeypatch.setattr(translator, "_make_refinement_request", fake_request)
    monkeypatch.setattr("src.core.refine.plus_pipeline.refine_plus_segment", fake_plus)

    plus_result = await translator.refine_chunks(
        translated_chunks=["one"],
        original_chunks=[{"source_text": "src"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        prompt_options={"refine_plus": True},
    )
    assert plus_result == ["one|plus"]
    assert one_pass == []

    ape_result = await translator.refine_chunks(
        translated_chunks=["one"],
        original_chunks=[{"source_text": "src"}],
        target_language="French",
        model_name="test-model",
        api_endpoint="https://example.test/v1",
        auto_adjust_context=False,
        context_window=8192,
        prompt_options={"refine_plus": False},
    )
    assert ape_result == ["one|one-pass"]
    assert len(one_pass) == 1


def test_cost_estimator_classic_refine_only_is_one_pass():
    from src.core.pricing.estimator import CostEstimator

    estimator = CostEstimator("openai", "gpt-4o-mini", {"input": 1.0, "output": 1.0})
    text = "Once upon a time there was a garden. " * 40
    classic_only = estimator.estimate(
        text, "English", "French", {"refine": True, "refine_only": True},
    )
    assert classic_only["passes"] == 1


@pytest.mark.asyncio
async def test_json_notes_without_translation_keeps_draft():
    class NotesOnlyLLM(_ScriptedLLM):
        async def __call__(self, prompt_pair, *, temperature=None):
            kind = _classify(prompt_pair)
            self.calls.append({"kind": kind, "temperature": temperature})
            if kind == "pass4":
                return _wrap(json.dumps({"notes": SECRET, "omissions": [SECRET]}))
            return await super().__call__(prompt_pair, temperature=temperature)

    llm = NotesOnlyLLM()
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    assert SECRET not in result.text
    assert result.text == GOOD


@pytest.mark.asyncio
async def test_unparseable_json_blob_keeps_draft():
    class BrokenJSONLLM(_ScriptedLLM):
        async def __call__(self, prompt_pair, *, temperature=None):
            kind = _classify(prompt_pair)
            self.calls.append({"kind": kind, "temperature": temperature})
            if kind == "pass4":
                return _wrap('{ "notes": "' + SECRET)
            return await super().__call__(prompt_pair, temperature=temperature)

    llm = BrokenJSONLLM()
    result = await refine_plus_segment(
        draft=GOOD,
        source=SOURCE,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    assert SECRET not in result.text
    assert result.text == GOOD
    assert result.text.strip()[:1] != "{"


@pytest.mark.asyncio
async def test_structure_guard_rejects_placeholder_loss():
    draft = "Lin met Zhao [[0]] in the garden in 2012."
    stripped = "Lin met Zhao in the garden in 2012."
    llm = _ScriptedLLM(
        pass1_text=stripped,
        pass2_text=stripped,
        pass3_text=stripped,
        pass4_text=stripped,
    )
    result = await refine_plus_segment(
        draft=draft,
        source=draft,
        target_language="English",
        prompt_options=_options(True),
        llm_generate=llm,
    )
    assert "[[0]]" in result.text
    assert result.text == draft


class _MemoryCkpt:
    def __init__(self):
        self.states = {}

    def save_refinement_state(self, translation_id, state, scope=None):
        self.states[translation_id] = dict(state)
        return True

    def load_refinement_state(self, translation_id, scope=None):
        state = self.states.get(translation_id)
        return dict(state) if state else None

    def delete_refinement_state(self, translation_id, scope=None):
        self.states.pop(translation_id, None)
        return True


class _Resp:
    def __init__(self, content):
        self.content = content
        self.prompt_tokens = 10
        self.completion_tokens = 10
        self.context_limit = 4096


@pytest.mark.asyncio
async def test_txt_rate_limit_after_pass_2_keeps_pass_index(monkeypatch):
    from src.core import translator
    from src.core.llm.exceptions import RateLimitError

    class FakeClient:
        async def close(self):
            return None

        async def detect_thinking_model(self):
            return None

        async def make_request(self, user, model, system_prompt=None, **kwargs):
            class Pair:
                pass

            Pair.system = system_prompt or ""
            Pair.user = user or ""
            kind = _classify(Pair())
            if kind == "pass3":
                raise RateLimitError("429 Too Many Requests", provider="test")
            if kind == "pass4":
                return _Resp(_json_body("final", GOOD))
            return _Resp(_wrap(GOOD))

    monkeypatch.setattr(translator, "create_llm_client", lambda *args, **kwargs: FakeClient())
    checkpoint = _MemoryCkpt()

    with pytest.raises(RateLimitError) as exc_info:
        await translator.refine_chunks(
            translated_chunks=[GOOD],
            original_chunks=[{"source_text": SOURCE}],
            target_language="English",
            model_name="test-model",
            api_endpoint="https://example.test/v1",
            auto_adjust_context=False,
            context_window=8192,
            prompt_options=_options(True),
            checkpoint_manager=checkpoint,
            translation_id="txt_plus_429",
        )

    state = exc_info.value.refinement_state or checkpoint.states.get("txt_plus_429")
    assert state is not None
    assert state["pass_index"] == 3
    assert checkpoint.states["txt_plus_429"]["pass_index"] == 3
    assert state["version"] == 2


@pytest.mark.asyncio
async def test_epub_plus_checkpoint_v2_after_one_pass(monkeypatch):
    from src.core.epub import xhtml_translator
    from src.core.llm.exceptions import RateLimitError

    async def fake_plus(**kwargs):
        on_pass = kwargs.get("on_pass_complete")
        draft = kwargs["draft"]
        if on_pass:
            maybe = on_pass(2, f"{draft}|p1", False)
            if hasattr(maybe, "__await__"):
                await maybe
        raise RateLimitError("429 Too Many Requests", provider="test")

    monkeypatch.setattr("src.core.refine.plus_pipeline.refine_plus_segment", fake_plus)
    checkpoint = _MemoryCkpt()
    chunk = {"text": "Hello world", "local_tag_map": {}, "global_indices": []}

    with pytest.raises(RateLimitError) as exc_info:
        await xhtml_translator._refine_epub_chunks(
            translated_chunks=["Hello world"],
            chunks=[chunk],
            target_language="French",
            model_name="test-model",
            llm_client=object(),
            context_manager=None,
            placeholder_format=("[", "]"),
            log_callback=None,
            prompt_options={"refine_plus": True},
            checkpoint_manager=checkpoint,
            translation_id="epub_plus_v2",
        )

    state = exc_info.value.refinement_state or checkpoint.states.get("epub_plus_v2")
    assert state["version"] == 2
    assert state["pass_index"] == 2
    assert state["segment_current"] == "Hello world|p1"


@pytest.mark.asyncio
async def test_srt_plus_checkpoint_v2_after_one_pass(monkeypatch):
    from src.core import subtitle_translator
    from src.core.llm.exceptions import RateLimitError

    async def fake_plus(**kwargs):
        on_pass = kwargs.get("on_pass_complete")
        draft = kwargs["draft"]
        if on_pass:
            maybe = on_pass(2, f"{draft}|p1", False)
            if hasattr(maybe, "__await__"):
                await maybe
        raise RateLimitError("429 Too Many Requests", provider="test")

    monkeypatch.setattr("src.core.refine.plus_pipeline.refine_plus_segment", fake_plus)
    checkpoint = _MemoryCkpt()

    with pytest.raises(RateLimitError) as exc_info:
        await subtitle_translator.refine_subtitle_translations(
            translations={0: "Hello"},
            target_language="French",
            model_name="test-model",
            llm_client=object(),
            prompt_options={"refine_plus": True},
            checkpoint_manager=checkpoint,
            translation_id="srt_plus_v2",
            refinement_output_filepath="/tmp/out.srt",
        )

    state = exc_info.value.refinement_state or checkpoint.states.get("srt_plus_v2")
    assert state["version"] == 2
    assert state["pass_index"] == 2
    assert "[0]Hello" in (state.get("segment_current") or "")


def test_sample_markdown_uses_i18n_phase_labels():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "src/web/static/js/sample/sample-table.js").read_text(
        encoding="utf-8"
    )
    assert "t('sample:phase_translated')" in src
    assert "t('sample:phase_refined')" in src
    assert "emitBlock('Translated'" not in src
    assert "emitBlock('Refined'" not in src

