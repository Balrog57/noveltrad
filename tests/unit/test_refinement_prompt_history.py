from src.prompts.prompts import generate_refinement_prompt
from src.core.translator import REFINEMENT_PROMPT_VERSION


def test_refinement_prompt_version_is_v3():
    assert REFINEMENT_PROMPT_VERSION == "source-aware-three-pass-v3"


def test_refinement_prompt_anchors_source_and_full_history():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        refinement_phase=3,
        source_translation="source passage",
        initial_translation="initial draft",
        previous_refined_translation="previous revision",
    )

    assert "pass 3/3" in prompt.system
    assert "natural human French" in prompt.system
    assert "SOURCE TEXT (meaning anchor)" in prompt.user
    assert "source passage" in prompt.user
    assert "INITIAL TRANSLATION" in prompt.user
    assert "initial draft" in prompt.user
    assert "PREVIOUS REFINEMENT" in prompt.user
    assert "previous revision" in prompt.user


def test_refinement_phase_guidance_is_strengthened():
    context = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        refinement_phase=1,
    )
    correction = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        refinement_phase=2,
    )
    final = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
        refinement_phase=3,
    )

    assert "calque" in context.system
    assert "entirely in the target language" in context.system
    assert "idiomatic target-language phrasing" in correction.system
    assert "natural human French" in final.system
    assert "smallest changes" not in final.system
    assert "never leave source-language wording" in final.system


def test_refinement_prompt_remains_monolingual_without_source():
    prompt = generate_refinement_prompt(
        draft_translation="texte déjà traduit",
        target_language="French",
        refinement_phase=1,
    )

    assert "pass 1/3" in prompt.system
    assert "SOURCE TEXT (meaning anchor)" not in prompt.user
