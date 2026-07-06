## 2025-07-06 - SQLite bulk insert performance
**Learning:** node-sqlite3-wasm executes queries outside of a transaction by default. For bulk inserts like `importTmx`, this causes a massive performance hit because each insert triggers an fsync.
**Action:** Always wrap bulk database operations (e.g., loops containing `db.prepare().run()`) in `db.exec("BEGIN TRANSACTION")` and `db.exec("COMMIT")` (with a try/catch `ROLLBACK`) to vastly improve performance.
