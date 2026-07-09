## 2024-07-08 - SQLite Mass Inserts Missing Transactions
**Learning:** In node-sqlite3-wasm, executing multiple inserts or updates in a loop without explicit transaction blocks `BEGIN TRANSACTION` / `COMMIT` causes SQLite to wrap every single execution in its own transaction, severely impacting performance for bulk operations. This pattern is missing in `importTmx` function of `TranslationMemoryEngine.ts` where we can insert thousands of translation units in a single operation.
**Action:** When performing bulk writes in a loop, always manually wrap the operations with `db.exec('BEGIN TRANSACTION')` and `db.exec('COMMIT')` along with a try/catch `ROLLBACK` for error handling.

## 2024-07-09 - O(N²) Array Lookups During History Reconstruction
**Learning:** In `HistoryRepository.ts`, `applyIncrementalChanges` was using `Array.findIndex` inside a loop iterating over changes to find existing paragraphs by their index. For large snapshots with thousands of paragraphs, this results in an O(N²) time complexity, creating a significant UI block / latency when navigating history or loading snapshots.
**Action:** Replaced the array lookup with a `Map<number, Paragraph>` to index paragraphs by `indexInChapter` once up front, changing the time complexity to O(N) and eliminating the bottleneck during incremental snapshot reconstruction.
