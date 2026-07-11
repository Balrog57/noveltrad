## 2024-05-24 - Array Updates Optimization in applyIncrementalChanges
**Learning:** Applying array changes using `findIndex` inside a loop of updates causes O(N^2) complexity, significantly degrading performance when reconciling large snapshot histories in `HistoryRepository`.
**Action:** Always pre-index base arrays into a `Map` to perform O(1) lookups, changing the complexity to O(N) while maintaining correctness.
