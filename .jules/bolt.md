## 2024-08-17 - Eliminate unnecessary fetchall() calls in SQLite loops
**Learning:** When iterating over a cursor, using `fetchall()` loads the entire result set into memory at once, which can create memory pressure and slow down operations for large data sets. Iterating directly over the cursor avoids this intermediate allocation.
**Action:** Avoid `.fetchall()` when iterating over database results, instead iterate directly over the cursor (`for row in cursor:`).
