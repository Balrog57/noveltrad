## 2024-06-15 - Fixed infinite recursion loop in NLLBEngine
**Learning:** `NLLBEngine._translate_multiblock` expects input split by `\n\s*\n+` (paragraph breaks), but `NLLBEngine.translate` was calling it simply `if "\n" in text:`. This caused an infinite recursion `RecursionError` when text had single newlines instead of paragraph breaks.
**Action:** Be careful with recursive text-splitting methods to ensure the condition to delegate to them matches the actual split regex, otherwise you'll hit infinite loops. Used `re.search(r"\n\s*\n+", text)` instead.
## 2024-06-21 - SentencePiece batch encoding/decoding returns a list of lists
**Learning:** When using SentencePiece batch methods (`sp.encode` with a list of strings, `sp.decode` with a list of token lists), you must ensure that mocks in unit tests correctly return list of lists instead of flat lists for batch processing, otherwise test assertions will fail because the batch list structures are malformed.
**Action:** When updating systems to use batch ML APIs, always review associated test mocks and ensure their return types adapt dynamically based on whether the input is a single item or a list of items (batch).
