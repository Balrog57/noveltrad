## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-25 - Native Batch Processing for NLLBEngine and SentencePiece
**Learning:** Working with ML inference engines (`ctranslate2`) and tokenizers (`sentencepiece`), loop-based individual encoding and decoding are slow bottlenecks. Both `ctranslate2` and `sentencepiece` offer robust, high-performance C++ level native batch implementations for processing data.
**Action:** Used `self._sp.encode` and `self._sp_target.decode` natively with batch inputs (list of texts or list of token lists) in `NLLBEngine._translate_multiblock` and `translate_batch` to maximize throughput instead of running individual for-loops over sequences in Python. Always prefer bulk C++ endpoints over Python iteration.
