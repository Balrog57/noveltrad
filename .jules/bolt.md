## 2024-06-11 - Add SQLite Bulk Transactions
**Learning:** `node-sqlite3-wasm` lacks a built-in `.transaction()` wrapper function. When performing bulk writes in loops (e.g., in repository methods like `createMany`), the default SQLite behavior wraps each `.run()` call in its own transaction (N+1 behavior), which causes a massive I/O bottleneck.
**Action:** When performing bulk writes in loops, manually wrap the `.run()` executions with `this.db.exec('BEGIN TRANSACTION')` and `this.db.exec('COMMIT')` (including a try/catch `ROLLBACK`) to batch the SQLite operations.
