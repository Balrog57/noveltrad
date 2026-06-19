## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-16 - SentencePiece native batching optimization
**Learning:** In the `NLLBEngine`, tokenization and decoding using `sentencepiece` was originally implemented as Python `for` loops. While functional, this leaves significant performance on the table because `sentencepiece` provides highly optimized C++ native batch processing methods `sp.encode(list_of_strings)` and `sp.decode(list_of_token_lists)`.
**Action:** When working with ML inference engines and tokenizers, always review if there are native batch methods rather than looping in Python. Pass lists of sequences directly to methods like `sp.encode()` and `sp.decode()` to maximize throughput.
