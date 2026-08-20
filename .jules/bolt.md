## 2026-08-18 - Database Cursor Iteration
**Learning:** Avoid using `cursor.fetchall()` when simply iterating over SQLite query results. Iterate directly over the cursor to lazily fetch rows, reducing memory pressure by avoiding O(N) intermediate list allocations.
**Action:** Iterate directly over the database cursor (e.g., `for row in cursor:`) rather than loading all results into an intermediate list using `fetchall()`.
