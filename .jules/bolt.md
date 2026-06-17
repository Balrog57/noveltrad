## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.
## 2024-06-15 - Used native batch sentencepiece tokenization for NLLB translate_batch
**Learning:** `sentencepiece` processors implemented natively in C++ can encode and decode lists of strings directly. It is much faster (roughly 50-70% speedup on encoding and decoding lists of tokens) compared to calling `.encode` or `.decode` within a python `for` loop.
**Action:** Whenever using `sentencepiece` with list of strings, pass the list directly instead of looping through each text and tokenizing them one by one.
