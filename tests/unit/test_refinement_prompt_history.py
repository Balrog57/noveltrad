from src.prompts.prompts import generate_refinement_prompt, generate_subtitle_refinement_block_prompt


def test_tbl_refinement_prompt_is_one_pass_literary():
    prompt = generate_refinement_prompt(
        draft_translation="draft",
        target_language="French",
    )

    assert "pass 3/3" not in prompt.system
    assert "CURRENT REFINEMENT STAGE" not in prompt.system
    assert "REWRITE it with perfect literary French style" in prompt.system
    assert "SOURCE TEXT (meaning anchor)" not in prompt.user
    assert "Provide your refined version now:" in prompt.user


def test_tbl_subtitle_refinement_prompt_is_one_pass():
    prompt = generate_subtitle_refinement_block_prompt(
        subtitle_blocks=[(0, "draft cue")],
        target_language="French",
    )

    assert "pass 3/3" not in prompt.system
    assert "SOURCE SUBTITLES" not in prompt.user
    assert "Provide your refined block now:" in prompt.user
