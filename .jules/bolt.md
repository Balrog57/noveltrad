## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-08-01 - Native Batch Processing for SentencePiece
**Learning:** In inference engines like `NLLBEngine` handling multiblock text or processing items in `translate_batch`, calling `.encode()` and `.decode()` inside a Python loop creates a major performance bottleneck for throughput because it repeatedly calls from Python into native code for small segments. SentencePiece has native support for encoding and decoding lists of strings directly.
**Action:** Always batch texts into lists and call `sp.encode(text_list)` and `sp.decode(token_list)` to push the looping logic down to the underlying C++ extension and maximize throughput during data prep and cleanup for model inference.
