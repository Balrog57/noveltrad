## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-29 - Native SentencePiece Batching
**Learning:** Looping over inputs in Python and passing them individually to SentencePiece's `encode` and `decode` methods is a measurable performance bottleneck during inference. The library uses C++ bindings that are optimized for list/batch inputs.
**Action:** When working with ML inference engines (`ctranslate2`) and tokenizers (`sentencepiece`), always use native batch processing methods by passing lists of strings/tokenized sequences directly to methods like `sp.encode()` and `sp.decode()` instead of looping over them in Python to maximize throughput. Also ensure mock classes in tests handle these nested lists properly.
