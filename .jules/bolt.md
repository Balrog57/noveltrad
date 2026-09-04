# Bolt's Journal — Critical Learnings Only

Performance notes specific to this codebase. Routine optimizations are not logged here.

## 2026-08-28 - TagPreserver re-scanned every HTML segment

**Learning:** `preserve_tags_and_technical_content()` called `TechnicalContentDetector.find_all_technical_content()` once per HTML segment for splitting *and again* per sub-segment in `_is_technical_content()` (~2000 calls on a 200-paragraph chapter). A two-pass scan (original text + marker text) plus carrying `is_technical` flags from the split eliminates per-segment work.

**Action:** When a pipeline already classifies segments, do not re-run the full detector in a downstream grouping loop. Profile with a call counter on hot methods before micro-optimizing regexes.

## 2026-08-29 - TagPreserver inline-pattern assignment was O(segments × patterns)

**Learning:** After the two-pass detector scan, `preserve_tags_and_technical_content()` still filtered all `inline_patterns` against every HTML text segment (~1M comparisons on a 500-paragraph chapter with dense `$V_{i}$` markers). Both lists are document-order, so a single advancing pointer assigns patterns in O(segments + patterns).

**Action:** When pre-scanned position-sorted items must be bucketed into contiguous segments, use a monotonic index — never re-scan the full pattern list per segment.

## 2026-09-04 - extract_text_and_positions re-scanned every prefix

**Learning:** `extract_text_and_positions()` called `fmt.remove_all(text[:start])` once per placeholder (~O(n²) on dense EPUB fallback chunks with 2k+ `[idN]` tags). Gaps between placeholders contain no markup, so a running `last_end` offset matches `_find_placeholder_positions()` in `token_alignment_fallback.py` — same math, single pass.

**Action:** When computing pure-text offsets in placeholder-heavy strings, never re-strip the prefix per item; accumulate gap lengths between sorted placeholder spans.
