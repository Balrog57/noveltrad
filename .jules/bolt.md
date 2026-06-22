## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-06-22 - SentencePiece Native Batching
**Learning:** When using ML components that deal with batched data, always read the documentation to see if they accept list inputs natively. In `NLLBEngine`, we were iterating through token sequences in Python and calling `.encode()` and `.decode()` individually. `sentencepiece` accepts lists of strings for `encode` and lists of tokens for `decode`, mapping to internal C++ batching logic that is substantially faster.
**Action:** Replaced Python loops with list batching for SentencePiece processors in `_translate_multiblock` and `translate_batch`. Always look for list inputs on native ML/tokenization wrappers instead of looping over single items.
