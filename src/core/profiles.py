"""Translation profiles (CDC Phase 2 — Technique / Littéraire / Courrier pro).

Each profile is a block of translation instructions injected into the
translate + proofread prompts, replacing the former single "tone" string.

Profiles are hardcoded (decision: en dur, not user-editable files) so the
behaviour is predictable and testable. The UI offers PROFILE_NAMES; the
pipeline reads get_profile(name)["instruction"].
"""

from __future__ import annotations

DEFAULT_PROFILE = "Général"

PROFILES: dict[str, dict[str, str]] = {
    "Général": {
        "name": "Général",
        "instruction": (
            "Produce a natural, accurate translation suitable for general-purpose "
            "content. Balance fidelity to the source with readability in the target "
            "language. No special register constraint."
        ),
        "tone_word": "neutral, natural",
    },
    "Technique": {
        "name": "Technique",
        "instruction": (
            "Prioritize precise technical terminology and consistency. Preserve code, "
            "identifiers, units, and acronyms verbatim where appropriate. Prefer the "
            "established technical term in the target language; keep it untranslated "
            "only if it is conventionally left in English in the field. Keep a precise, "
            "factual register."
        ),
        "tone_word": "technical, precise",
    },
    "Littéraire": {
        "name": "Littéraire",
        "instruction": (
            "Preserve the literary style, rhythm, tone, imagery and register of the "
            "original author. Prioritize fluency and elegance over literal wording; "
            "adapt idioms and figures of speech to their natural equivalent in the "
            "target language. Respect narration, dialogue cues and stylistic voice."
        ),
        "tone_word": "literary, elegant",
    },
    "Courrier pro": {
        "name": "Courrier pro",
        "instruction": (
            "Use a formal business-correspondence register. Be courteous, clear and "
            "concise; respect polite address conventions (formal 'vous' / 'Dear …' "
            "style) of the target language. Keep salutations and sign-offs appropriate "
            "to professional email/letter norms."
        ),
        "tone_word": "formal, professional correspondence",
    },
}

PROFILE_NAMES: list[str] = list(PROFILES.keys())


def get_profile(name: str | None) -> dict[str, str]:
    """Return the profile dict; falls back to Général if name is unknown."""
    if not name or name not in PROFILES:
        return PROFILES[DEFAULT_PROFILE]
    return PROFILES[name]
