from src.config import TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
from src.prompts.prompts import (
    generate_post_processing_prompt,
    generate_refinement_prompt,
    generate_subtitle_refinement_block_prompt,
)


def _combined(prompt) -> str:
    return f"{prompt.system}\n{prompt.user}"


def test_ape_refinement_prompt_is_one_pass():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        source_translation="source sentence",
        source_language="English",
    )

    assert "pass 3/3" not in prompt.system
    assert "CURRENT REFINEMENT STAGE" not in prompt.system
    assert "automatic post-editing" in prompt.system
    assert "You are a professional English to French translator" in prompt.system
    assert prompt.system.count("Do not explain.") == 1
    assert "Do not explain." not in prompt.user
    assert "# DRAFT TO REFINE" not in prompt.user
    assert "[Translation Tasks]" in prompt.user
    assert "[Translation Tasks]" not in prompt.system
    assert "English → French" in prompt.user
    assert "The English segment:" in prompt.user
    assert "source sentence" in prompt.user
    assert "The French candidate to post-edit:" in prompt.user
    assert "draft" in prompt.user
    assert TRANSLATE_TAG_IN in prompt.system
    assert TRANSLATE_TAG_OUT in prompt.system
    assert prompt.user.endswith(
        f"Start with {TRANSLATE_TAG_IN} and end with {TRANSLATE_TAG_OUT}."
    )
    assert "The multiple French translations:" not in prompt.user


def test_ape_refinement_includes_numbered_candidates():
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


def test_ape_refinement_omits_empty_candidate_block():
    prompt = generate_refinement_prompt(
        draft_translation="current draft",
        target_language="French",
        initial_translation="current draft",
        previous_refined_translation="",
    )

    assert "The multiple French translations:" not in prompt.user
    assert "The French candidate to post-edit:" in prompt.user


def test_ape_post_processing_alias_forwards_source():
    prompt = generate_post_processing_prompt(
        translated_text="draft",
        target_language="French",
        source_translation="origine",
        source_language="Italian",
    )

    assert "The Italian segment:" in prompt.user
    assert "origine" in prompt.user
    assert "Italian → French" in prompt.user
    assert "[Translation Tasks]" in prompt.user


def test_ape_refinement_uses_configured_language_codes_only():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        source_translation="hello",
        source_language="English",
        prompt_options={
            "source_language_code": "en",
            "target_language_code": "fr",
        },
    )

    assert "English (en) → French (fr)" in prompt.user
    invented = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        source_language="English",
    )
    assert "English → French" in invented.user
    assert "(en)" not in invented.user


def test_ape_style_instructions_fold_into_style_task():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        additional_instructions="Keep the narrator wry.",
    )

    assert "Keep the narrator wry." in prompt.user
    assert "[Translation Tasks]" in prompt.user
    numbered_lines = [
        line for line in prompt.user.splitlines()
        if line[:2].rstrip(".").isdigit() or (line and line[0].isdigit() and ". " in line[:4])
    ]
    assert any("Keep the narrator wry." in line for line in numbered_lines)
    assert not any(line.endswith("Keep the narrator wry.") and line.startswith("6.") for line in numbered_lines)


def test_ape_subtitle_refinement_prompt_is_one_pass():
    prompt = generate_subtitle_refinement_block_prompt(
        subtitle_blocks=[(0, "draft cue")],
        source_subtitle_blocks=[(0, "source cue")],
        target_language="French",
        source_language="English",
    )

    assert "pass 3/3" not in prompt.system
    assert "automatic post-editing" in prompt.system
    assert "[Translation Tasks]" in prompt.user
    assert "[Translation Tasks]" not in prompt.system
    assert prompt.system.count("Do not explain.") == 1
    assert "# SUBTITLES TO REFINE" not in prompt.user
    assert "English → French" in prompt.user
    assert "The English segment:" in prompt.user
    assert "[0]source cue" in prompt.user
    assert "The French candidate to post-edit:" in prompt.user
    assert "The multiple French translations:" not in prompt.user
    combined = _combined(prompt)
    assert combined.count("Only output the refined translation, do not explain.") == 0
