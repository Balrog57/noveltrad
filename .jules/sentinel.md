
## 2026-07-19 - Flawed Path Validation Bypass
**Vulnerability:** Path traversal check bypass in `assertWithinProject`.
**Learning:** Validating a target path against its own dynamic parent directory (e.g. `assertWithinProject(path.dirname(targetPath), targetPath)`) trivially passes the path containment check. It does not validate if the path is within the intended, authorized root directory.
**Prevention:** Always validate a target path against a fixed, trusted boundary (e.g., the configured project root), rather than a derivative of the user-provided path itself. Use absolute paths like `basePath` directly or use `assertSafeProjectPath`.
