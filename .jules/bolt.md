## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-23 - Optimize NLLB Tokenizer Batch Processing
**Learning:** When using SentencePiece models internally (`self._sp.encode` / `self._sp_target.decode`), it's significantly faster to pass lists of strings directly instead of iterating in Python. Natively delegating the array handling to the C++ SentencePiece extension maximizes throughput when working with batched inputs.
**Action:** Always prefer native batch methods for inference libraries and tokenizers (`encode(list_of_strings)`, `decode(list_of_token_lists)`) over Python list comprehensions or loops.
