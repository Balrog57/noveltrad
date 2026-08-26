# Bolt's Journal — Critical Learnings Only

Performance notes specific to the NovelTrad codebase. Routine optimizations are not logged here.

## 2026-08-26 - Tag extraction beats subtree depth tracking for EPUB DOM walks

**Learning:** Replacing an O(n×depth) ancestor walk in `boilerplate_filter` with depth-tracked `iterwalk` looked algorithmically better, but measured only ~1.1× on realistic nested-widget bodies because `iterwalk`'s start/end event overhead dominates when widget subtrees are shallow. In contrast, `TagClassifier` ran a 15-tag substring scan on every placeholder pair during HTML chunking; extracting the tag name once with a compiled regex and doing a set lookup measured ~5× faster on representative tag_map workloads.

**Action:** Profile hot paths that run per-placeholder/per-chunk before chasing DOM traversal complexity. Prefer O(1) tag-name extraction over repeated substring scans in chunking code.
