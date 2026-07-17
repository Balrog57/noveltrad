## 2024-05-24 - Array Updates Optimization in applyIncrementalChanges
**Learning:** Applying array changes using `findIndex` inside a loop of updates causes O(N^2) complexity, significantly degrading performance when reconciling large snapshot histories in `HistoryRepository`.
**Action:** Always pre-index base arrays into a `Map` to perform O(1) lookups, changing the complexity to O(N) while maintaining correctness.

## 2024-07-08 - SQLite Mass Inserts Missing Transactions
**Learning:** In node-sqlite3-wasm, executing multiple inserts or updates in a loop without explicit transaction blocks `BEGIN TRANSACTION` / `COMMIT` causes SQLite to wrap every single execution in its own transaction, severely impacting performance for bulk operations. This pattern is missing in `importTmx` function of `TranslationMemoryEngine.ts` where we can insert thousands of translation units in a single operation.
**Action:** When performing bulk writes in a loop, always manually wrap the operations with `db.exec('BEGIN TRANSACTION')` and `db.exec('COMMIT')` along with a try/catch `ROLLBACK` for error handling.

## 2024-07-10 - SQLite Mass Inserts Missing Transactions (RagEngine)
**Learning:** The missing `BEGIN TRANSACTION` issue in `node-sqlite3-wasm` for mass inserts also applies to the RagEngine's `storeEmbeddings` method. Because SQLite commits each query independently by default, inserting massive arrays of vector embeddings one by one without an explicit transaction wrapper causes severe O(N) I/O bottleneck overhead, increasing embedding indexing times significantly.
**Action:** We wrapped the loop inside `storeEmbeddings` with explicit `this.db.exec('BEGIN TRANSACTION')` and `this.db.exec('COMMIT')` commands, which resolved the latency. When doing so, it is critical to also mock the `exec` method in the `MockDatabase` object within the test files (e.g. `rag-engine.spec.ts`) to prevent test suite failures with `TypeError: this.db.exec is not a function`.

## 2024-07-17 - Array Lookups Optimization with Set
**Learning:** Using `Array.includes()` inside loops or array filters like `Array.filter()` creates an O(N*M) time complexity bottleneck. This degrades performance significantly when dealing with large datasets, such as arrays of paragraphs in history snapshots or auto-saves.
**Action:** Pre-convert the identifier array (or list of items to match against) into a `Set` before filtering or looping, and use `Set.has()` for O(1) lookups, changing overall complexity to O(N).
