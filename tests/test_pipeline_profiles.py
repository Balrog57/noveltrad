"""Tests that pipeline profiles map to the expected stage orders.

We test the data module directly so these tests stay fast and do not
need a running backend or spawned worker processes.
"""

from __future__ import annotations

import unittest

from src.backend.orchestrator.pipeline import (
    ALL_STAGES,
    ASSEMBLER,
    FAST_TRANSLATOR,
    LEXICON_BUILDER,
    PARSER,
    PROFILE_BALANCED,
    PROFILE_ECO,
    PROFILE_PREMIUM,
    REVIEWER,
    TERMINOLOGY_RESEARCHER,
    VALID_PROFILES,
    get_profile_order,
)


class ProfileOrderTests(unittest.TestCase):
    def test_all_known_profiles(self) -> None:
        self.assertEqual(VALID_PROFILES, {"eco", "balanced", "premium"})

    def test_profile_eco_is_minimal(self) -> None:
        self.assertEqual(PROFILE_ECO, (PARSER, FAST_TRANSLATOR, ASSEMBLER))

    def test_profile_balanced_has_ten_stages(self) -> None:
        # Balanced = full LLM refinement + reviewer, but no separate terminology researcher
        self.assertEqual(len(PROFILE_BALANCED), 10)
        self.assertIn(PARSER, PROFILE_BALANCED)
        self.assertIn(FAST_TRANSLATOR, PROFILE_BALANCED)
        self.assertIn(LEXICON_BUILDER, PROFILE_BALANCED)
        self.assertIn(REVIEWER, PROFILE_BALANCED)
        self.assertNotIn(TERMINOLOGY_RESEARCHER, PROFILE_BALANCED)
        self.assertEqual(PROFILE_BALANCED[-1], ASSEMBLER)

    def test_profile_premium_has_all_twelve_stages(self) -> None:
        self.assertEqual(len(PROFILE_PREMIUM), 12)
        self.assertIn(TERMINOLOGY_RESEARCHER, PROFILE_PREMIUM)
        self.assertIn(REVIEWER, PROFILE_PREMIUM)
        self.assertEqual(PROFILE_PREMIUM[-1], ASSEMBLER)

    def test_get_profile_order_defaults_to_balanced(self) -> None:
        self.assertEqual(get_profile_order(None), PROFILE_BALANCED)
        self.assertEqual(get_profile_order("unknown"), PROFILE_BALANCED)

    def test_get_profile_order_respects_request(self) -> None:
        self.assertEqual(get_profile_order("eco"), PROFILE_ECO)
        self.assertEqual(get_profile_order("balanced"), PROFILE_BALANCED)
        self.assertEqual(get_profile_order("premium"), PROFILE_PREMIUM)

    def test_premium_equals_default_pipeline_order(self) -> None:
        from src.backend.orchestrator.pipeline import DEFAULT_PIPELINE_ORDER

        self.assertEqual(PROFILE_PREMIUM, DEFAULT_PIPELINE_ORDER)
        self.assertEqual(set(PROFILE_PREMIUM), set(ALL_STAGES))


if __name__ == "__main__":
    unittest.main()
