# Bolt's Journal — Critical Learnings Only

## 2026-08-27 - Glossary regex cache vs Python's internal cache
**Learning:** `filter_glossary()` calls `re.findall()` with a distinct pattern per glossary term on every translation chunk. Python's internal regex cache does not meaningfully help because each term is a unique pattern string; `lru_cache` on `re.compile()` for `(alt, flags)` cuts per-chunk scan time ~15% for 500-term glossaries.
**Action:** For per-term dynamic regex in hot loops, cache compiled `re.Pattern` objects explicitly — do not rely on `re.findall(str_pattern, ...)`.
