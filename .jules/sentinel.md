## 2024-11-20 - Defense-in-Depth Path Traversal Fix
**Vulnerability:** Zod string schemas at the Electron IPC boundary did not reject raw `../` or URL-encoded `%2e%2e%2f` sequences for file path inputs.
**Learning:** Even though `assertWithinProject` exists downstream, it is not consistently applied to all path handlers, and its naive `path.resolve` check is bypassed by absolute paths like `/etc/passwd`. Electron IPC uses the Structured Clone algorithm, passing strings exactly as they are without URL-decoding, making regex validations against both forms necessary.
**Prevention:** Apply a comprehensive regex (`/(?:\.|%2e){2}(?:$|\/|\\|%2f|%5c)/i`) directly in the Zod schemas at the IPC boundary (`project.ts`) to reject malicious traversal sequences as early as possible.
