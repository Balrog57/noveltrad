# Bolt's Journal — Critical Learnings Only

Performance notes specific to this codebase. Routine optimizations are not logged here.

## 2026-08-28 - TagPreserver re-scanned every HTML segment

**Learning:** `preserve_tags_and_technical_content()` called `TechnicalContentDetector.find_all_technical_content()` once per HTML segment for splitting *and again* per sub-segment in `_is_technical_content()` (~2000 calls on a 200-paragraph chapter). A two-pass scan (original text + marker text) plus carrying `is_technical` flags from the split eliminates per-segment work.

**Action:** When a pipeline already classifies segments, do not re-run the full detector in a downstream grouping loop. Profile with a call counter on hot methods before micro-optimizing regexes.

## 2026-08-29 - TagPreserver inline-pattern assignment was O(segments × patterns)

**Learning:** After the two-pass detector scan, `preserve_tags_and_technical_content()` still filtered all `inline_patterns` against every HTML text segment (~1M comparisons on a 500-paragraph chapter with dense `$V_{i}$` markers). Both lists are document-order, so a single advancing pointer assigns patterns in O(segments + patterns).

**Action:** When pre-scanned position-sorted items must be bucketed into contiguous segments, use a monotonic index — never re-scan the full pattern list per segment.

## 2026-09-02 - Orchestrator duplicated EPUB/DOCX preprocessing

**Learning:** `GenericTranslationOrchestrator` called `extract_content` + `preserve_structure` before `translate_content`, but EPUB/DOCX adapters ignore those results and rerun the same pipeline inside `translate_xhtml_simplified` / `DocxTranslationAdapter.translate_content`. Every chapter paid for two full extract+preserve passes before the first LLM call.

**Action:** For adapters with `translate_content`, skip orchestrator-level extract/preserve and delegate directly. Profile per-chapter startup if adding new adapter fast-paths.
