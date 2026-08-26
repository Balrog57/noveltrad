from src.prompts.prompts import (
    generate_post_processing_prompt,
    generate_refinement_prompt,
    generate_subtitle_refinement_block_prompt,
)


def test_hy_mt2_refinement_prompt_is_one_pass():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        source_translation="source sentence",
        source_language="English",
    )

    assert "pass 3/3" not in prompt.system
    assert "CURRENT REFINEMENT STAGE" not in prompt.system
    assert "[Translation Tasks]" in prompt.system
    assert "Only output the refined translation, do not explain." in prompt.system
    assert "The English segment:" in prompt.user
    assert "source sentence" in prompt.user
    assert "Provide your refined version now:" in prompt.user


def test_hy_mt2_refinement_includes_numbered_candidates():
    prompt = generate_refinement_prompt(
        draft_translation="current draft",
        target_language="French",
        initial_translation="first draft",
        previous_refined_translation="earlier polish",
    )

    assert "The multiple French translations:" in prompt.user
    assert "1. Initial translation:" in prompt.user
    assert "first draft" in prompt.user
    assert "earlier polish" in prompt.user
    assert "current draft" in prompt.user


def test_hy_mt2_post_processing_alias_forwards_source():
    prompt = generate_post_processing_prompt(
        translated_text="draft",
        target_language="French",
        source_translation="origine",
        source_language="Italian",
    )

    assert "The Italian segment:" in prompt.user
    assert "origine" in prompt.user
    assert "[Translation Tasks]" in prompt.system


def test_hy_mt2_subtitle_refinement_prompt_is_one_pass():
    prompt = generate_subtitle_refinement_block_prompt(
        subtitle_blocks=[(0, "draft cue")],
        source_subtitle_blocks=[(0, "source cue")],
        target_language="French",
        source_language="English",
    )

    assert "pass 3/3" not in prompt.system
    assert "[Translation Tasks]" in prompt.system
    assert "Only output the refined translation, do not explain." in prompt.system
    assert "The English segment:" in prompt.user
    assert "[0]source cue" in prompt.user
    assert "Provide your refined block now:" in prompt.user
