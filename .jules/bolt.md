# Bolt's Journal — Critical Learnings Only

Performance notes specific to this codebase. Routine optimizations are not logged here.

## 2026-08-28 - TagPreserver re-scanned every HTML segment

**Learning:** `preserve_tags_and_technical_content()` called `TechnicalContentDetector.find_all_technical_content()` once per HTML segment for splitting *and again* per sub-segment in `_is_technical_content()` (~2000 calls on a 200-paragraph chapter). A two-pass scan (original text + marker text) plus carrying `is_technical` flags from the split eliminates per-segment work.

**Action:** When a pipeline already classifies segments, do not re-run the full detector in a downstream grouping loop. Profile with a call counter on hot methods before micro-optimizing regexes.
