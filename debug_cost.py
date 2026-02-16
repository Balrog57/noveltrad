from src.core.cost_estimator import CostEstimator

text = "a" * 3500000
cost = CostEstimator.calculate_cost(text, "gpt-4o-mini")
print(f"Cost for 3.5M chars: {cost}")
print(f"Expected: 0.75")

text2 = "test"
cost_unknown = CostEstimator.calculate_cost(text2, "unknown-model")
cost_mini = CostEstimator.calculate_cost(text2, "gpt-4o-mini")
print(f"Cost Unknown: {cost_unknown}")
print(f"Cost Mini: {cost_mini}")
print(f"Equal? {cost_unknown == cost_mini}")
