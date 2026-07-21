## 2026-07-21 - Path Traversal check bypassing via self-dirname tautology
**Vulnerability:** A flawed path traversal validation in the `project:open` IPC handler used `assertWithinProject(path.dirname(validatedPath), validatedPath)`, which is always true and thus fails to provide any security against directory traversal.
**Learning:** Checking if a file path is within its own `dirname` is a tautology.
**Prevention:** Always validate untrusted input against a trusted base path, or use specific security checks for arbitrary paths like `assertSafeProjectPath`.
