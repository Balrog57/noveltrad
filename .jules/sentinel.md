## 2024-05-18 - Path Traversal in IPC Handler
**Vulnerability:** The `project:open` IPC handler allowed path traversal by validating a user-provided path against its own `dirname`, meaning `../../etc/passwd` would successfully validate as being "inside" `../../etc`.
**Learning:** Developers sometimes misunderstand `assertWithinProject(base, target)` by providing dynamic bases derived from the untrusted target itself instead of fixed boundary roots.
**Prevention:** Use `assertSafeProjectPath` for paths that can be placed anywhere (to block OS-critical paths and `..` sequences), or always ensure `assertWithinProject` receives a known, secure base path directory constant.
