
## 2025-02-25 - Legacy Glossary Migration O(1) Memory Fix
**Learning:** During database migrations, using `.fetchall()` on a cursor loads the entire result set into memory, creating an O(N) memory bottleneck for large legacy tables (like glossaries and glossary_terms).
**Action:** Replace `.fetchall()` with direct lazily iteration over the cursor (`for row in cursor:`) when migrating large database tables to achieve O(1) memory usage.
