import pytest

from src.core import subtitle_translator
from src.prompts.prompts import generate_subtitle_refinement_block_prompt


@pytest.mark.asyncio
async def test_srt_three_pass_refinement_keeps_source_and_history(monkeypatch):
    calls = []

    async def fake_once(**kwargs):
        calls.append(kwargs)
        phase = kwargs["prompt_options"]["refinement_phase"]
        return {0: f"pass-{phase}"}

    monkeypatch.setattr(
        subtitle_translator,
        "_refine_subtitle_translations_once",
        fake_once,
    )

    result = await subtitle_translator.refine_subtitle_translations(
        translations={0: "initial subtitle"},
        target_language="French",
        model_name="test-model",
        llm_client=object(),
        subtitle_blocks=[[{"number": "1", "text": "initial subtitle"}]],
        subtitle_positions={},
        source_subtitles=[{"number": "1", "text": "source subtitle"}],
    )

    assert result == {0: "pass-3"}
    assert [call["source_subtitles"][0]["text"] for call in calls] == [
        "source subtitle",
        "source subtitle",
        "source subtitle",
    ]
    assert [call["refinement_histories"][0] for call in calls] == [
        [],
        ["initial subtitle"],
        ["initial subtitle", "pass-1"],
    ]


def test_srt_refinement_prompt_contains_source_and_revisions():
    prompt = generate_subtitle_refinement_block_prompt(
        subtitle_blocks=[(0, "pass 2")],
        source_subtitle_blocks=[(0, "source line")],
        refinement_history={0: ["pass 1", "pass 2"]},
        target_language="French",
    )

    assert "source line" in prompt.user
    assert "Revision 1" in prompt.user
    assert "pass 1" in prompt.user
