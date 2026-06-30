## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## $(date +%Y-%m-%d) - Native Batch Processing with ML Engines
**Learning:** Python-level loops that cross the C++ boundary repeatedly during tokenization (`SentencePiece.encode()`) and detokenization (`SentencePiece.decode()`) introduce significant iteration overhead when processing large paragraph arrays or document chunks. Mocking these operations in tests requires ensuring the mocks support array inputs properly.
**Action:** Always utilize the native batch processing capability of tokenization libraries by passing lists of strings directly to `.encode()` and `.decode()` instead of wrapping single-item calls in Python loops.
