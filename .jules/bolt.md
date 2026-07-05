## 2024-05-15 - Missing Transaction Wrappers in node-sqlite3-wasm
**Learning:** `node-sqlite3-wasm` does not have a built-in `.transaction()` method, and by default, executing `.run()` inside a for-loop results in N separate transactions, causing massive disk I/O bottlenecks.
**Action:** When performing bulk writes (like `createMany` or `updateMany`), manually wrap the `.run()` executions with `this.db.exec('BEGIN TRANSACTION')` and `this.db.exec('COMMIT')` (including a try/catch `ROLLBACK` for safety) to significantly improve database insertion performance.
