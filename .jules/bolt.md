## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-26 - SentencePiece native batching optimization
**Learning:** In the NLLB translation engine, looping over strings to individually tokenize them using `sp.encode()` and decode them with `sp.decode()` creates a significant Python loop bottleneck, especially for multi-block text or batched API inputs.
**Action:** Always utilize the native batch processing capability of SentencePiece and CTranslate2 by passing the entire list of strings/tokens to `encode()` and `decode()` to shift the iteration to the C++ layer for maximum throughput.
