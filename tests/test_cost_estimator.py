import unittest
from src.core.cost_estimator import CostEstimator

class TestCostEstimator(unittest.TestCase):
    def test_estimate_tokens(self):
        text = "Hello world"
        # 11 chars / 3.5 = 3.14 -> 3 tokens
        self.assertEqual(CostEstimator.estimate_tokens(text), 3)
        
        text = ""
        self.assertEqual(CostEstimator.estimate_tokens(text), 0)

    def test_calculate_cost(self):
        # 1M tokens input cost for gpt-4o-mini is $0.15
        # 1M tokens output cost is $0.60
        # Total per 1M transaction (1:1 ratio) = $0.75
        
        # Test with 3,500,000 chars -> ~1,000,000 tokens
        text = "a" * 3500000
        cost = CostEstimator.calculate_cost(text, "gpt-4o-mini")
        
        # Expected cost ~ $0.75
        # Allow small margin due to float precision
        self.assertAlmostEqual(cost, 0.75, places=1)

    def test_get_formatted_cost(self):
        text = "Hello world"
        formatted = CostEstimator.get_formatted_cost(text)
        self.assertTrue(formatted.startswith("$"))

    def test_unknown_model_fallback(self):
        text = "test"
        # Unknown model should fallback to gpt-4o-mini pricing
        cost = CostEstimator.calculate_cost(text, "unknown-model")
        ref_cost = CostEstimator.calculate_cost(text, "gpt-4o-mini")
        self.assertEqual(cost, ref_cost)
