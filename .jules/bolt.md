## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.

## 2024-05-18 - Native Sentencepiece Batching
**Learning:** Python loops over inference engine wrappers (`sp.encode` and `sp.decode`) introduce significant latency. `sentencepiece` accepts arrays natively and handles C++ parallelism under the hood.
**Action:** Always prefer native batch arrays directly passed into `sentencepiece` over Python `for` loops.
