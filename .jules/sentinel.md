## 2025-05-18 - Path Traversal Vulnerability in IPC Boundaries
**Vulnerability:** The `assertWithinProject` function was vulnerable to URL-encoded path traversal attacks (`%2e%2e%2f`).
**Learning:** `path.resolve` does not decode URL-encoded strings, treating `%2e%2e` as a literal folder name. This allows traversal strings to bypass the `resolvedTarget.startsWith(resolvedBase)` check, potentially being evaluated later by filesystem APIs that decode or interpret them.
**Prevention:** Always validate and reject both raw (`../`) and URL-encoded (`%2e%2e%2f`) traversal sequences using a comprehensive regex *before* applying low-level filesystem resolution.
