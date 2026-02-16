class CostEstimator:
    """
    Utility class to estimate AI costs based on text length and model pricing.
    Prices are per 1 Million tokens (USD).
    """
    
    # Pricing as of Late 2024 / Early 2025 (Approximate)
    MODELS_PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00}, # Promos often apply
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00}, # Lower tier <128k
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "mistral-large": {"input": 2.00, "output": 6.00}
    }

    @staticmethod
    def estimate_tokens(text):
        """
        Estimate token count using a simple heuristic.
        English: ~4 chars per token.
        Multilingual/Code: ~3 chars per token.
        Using 3.5 as a safe average.
        """
        if not text: return 0
        return int(len(text) / 3.5)

    @staticmethod
    def calculate_cost(source_text, model_name="gpt-4o-mini"):
        """
        Calculate estimated cost for translating the source text.
        Assumes output length is roughly equal to input length.
        """
        if not source_text: return 0.0
        
        tokens = CostEstimator.estimate_tokens(source_text)
        
        # Default to mini if unknown
        pricing = CostEstimator.MODELS_PRICING["gpt-4o-mini"]
        
        # Try to find matching model key
        normalized_name = model_name.lower()
        # Sort keys by length descending to match longest key first (e.g. gpt-4o-mini before gpt-4o)
        sorted_keys = sorted(CostEstimator.MODELS_PRICING.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            if key in normalized_name:
                pricing = CostEstimator.MODELS_PRICING[key]
                break
        
        # Cost = (Input Tokens * Input Price) + (Output Tokens * Output Price)
        # We assume 1:1 translation ratio for safety
        input_cost = (tokens / 1_000_000) * pricing["input"]
        output_cost = (tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost

    @staticmethod
    def get_formatted_cost(source_text, model_name="gpt-4o-mini"):
        cost = CostEstimator.calculate_cost(source_text, model_name)
        return f"${cost:.4f}"
