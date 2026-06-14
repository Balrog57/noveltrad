## 2024-05-24 - [Optimize StateStore snapshot query]
**Learning:** Found an N+1 query problem in the backend's SQLite `StateStore.snapshot()` method, which executes 12 separate `SELECT COUNT(*)` queries on the `chunks` table every time the UI requests the pipeline state. Since this endpoint (`/pipeline/state`) is polled by the UI or fetched frequently, it's a hot path.
**Action:** Replaced the loop of multiple `COUNT` queries with a single `SELECT status, COUNT(*) FROM chunks GROUP BY status`. This significantly reduces database roundtrips and lock acquisitions.
