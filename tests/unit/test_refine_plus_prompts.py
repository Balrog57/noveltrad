"""Refine+ JSON extraction must never publish notes / ambiguity markers."""
from src.prompts.prompts import (
    PASS1_PLUS_FAITHFUL_INSTRUCTIONS,
    extract_json_object,
    generate_glossary_enforcement_prompt,
    generate_grammar_postedit_prompt,
    generate_omission_qa_prompt,
    generate_refinement_prompt,
    generate_style_refinement_prompt,
    published_text_from_payload,
    strip_ambiguity_markers,
)


def test_published_text_uses_translation_not_notes():
    payload = extract_json_object(
        '{"translation": "The garden was quiet.", '
        '"changes": [{"from": "yard", "to": "garden"}], '
        '"notes": "AMBIGUOUS subject", "omissions": ["secret"]}'
    )
    published = published_text_from_payload(payload, "translation", fallback="DRAFT")
    assert published == "The garden was quiet."
    assert "AMBIGUOUS" not in published
    assert "secret" not in published
    assert "notes" not in published.lower()


def test_published_text_uses_final_not_edits():
    payload = extract_json_object(
        '{"final": "She waited.", "edits": [{"before": "waited.", "after": "waited."}], '
        '"notes": "do not print"}'
    )
    published = published_text_from_payload(payload, "final", "translation", fallback="DRAFT")
    assert published == "She waited."
    assert "do not print" not in published


def test_strip_ambiguity_markers_from_plain_text():
    cleaned = strip_ambiguity_markers("Hello [[AMBIGUITY]] world [[AMBIGUÏTÉ]]")
    assert "AMBIGUITY" not in cleaned.upper()
    assert "Hello" in cleaned
    assert "world" in cleaned


def test_base_ape_prompt_is_unchanged_plain_output():
    pair = generate_refinement_prompt(
        draft_translation="She smiled.",
        target_language="French",
        has_placeholders=False,
    )
    blob = pair.system + pair.user
    assert "[[AMBIGUITY]]" not in blob
    assert '"notes"' not in blob
    assert "Chimera" in pair.system or "post-edit" in pair.system.lower() or "Automatic Post-Editing" in pair.system or "post" in pair.system.lower()


def test_pass1_plus_constraints_are_additive():
    assert "numbers" in PASS1_PLUS_FAITHFUL_INSTRUCTIONS.lower()
    assert "[[AMBIGUITY]]" in PASS1_PLUS_FAITHFUL_INSTRUCTIONS
    pair = generate_refinement_prompt(
        draft_translation="She smiled.",
        target_language="French",
        has_placeholders=False,
        additional_instructions=PASS1_PLUS_FAITHFUL_INSTRUCTIONS,
    )
    assert "strictly faithful" in pair.system.lower() or "strictly faithful" in pair.user.lower() or PASS1_PLUS_FAITHFUL_INSTRUCTIONS[:20] in pair.system + pair.user


def test_style_prompt_asks_for_translation_only():
    pair = generate_style_refinement_prompt(
        translation="She smiled.",
        target_language="French",
        register="literary",
    )
    assert "refined translation only" in pair.user.lower()
    assert "do not add or remove factual content" in pair.user.lower()


def test_glossary_and_grammar_prompts_request_json_sidecar():
    gloss = generate_glossary_enforcement_prompt(
        translation="She smiled.",
        glossary_pairs=[("Lin", "Lin")],
        target_language="French",
    )
    assert '"translation"' in gloss.user
    assert '"changes"' in gloss.user
    grammar = generate_grammar_postedit_prompt(
        translation="She smiled.",
        target_language="French",
        variant="fr-FR",
    )
    assert '"final"' in grammar.user
    assert '"edits"' in grammar.user
    omission = generate_omission_qa_prompt(
        source_text="She smiled.",
        translation="She grinned.",
        target_language="French",
    )
    assert '"omissions"' in omission.user
    assert '"additions"' in omission.user
