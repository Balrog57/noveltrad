## 2024-05-18 - Database Performance Pattern for Bulk Writes
**Learning:** `node-sqlite3-wasm` lacks a built-in `.transaction()` wrapper function. Default N+1 execution of `run()` statements within a loop causes significant massive I/O bottlenecks in SQLite.
**Action:** When performing bulk writes in loops (e.g. `createMany` or `updateMany`), manually wrap the `.run()` executions with `this.db.exec('BEGIN TRANSACTION')` and `this.db.exec('COMMIT')`, including a try/catch `ROLLBACK` for safety.
