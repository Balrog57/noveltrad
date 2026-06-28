## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2026-06-28 - Native Batch Processing with SentencePiece
**Learning:** `NLLBEngine` loop processing of SentencePiece `encode` and `decode` in python creates unnecessary python loop overhead. Instead, SentencePiece supports passing lists to its `encode` and `decode` routines, engaging its internal C++ optimizations for batched processing which increases throughput and removes python layer slowness.
**Action:** When working with ML inference engines and tokenizers like SentencePiece, always look for native batched API signatures (like accepting a list of strings instead of string) and prioritize them to skip python loops entirely and maximize system throughput.
