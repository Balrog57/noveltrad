## 2024-11-20 - Fix insecure mktemp vulnerability
**Vulnerability:** Found `tempfile.mktemp()` being used, which creates a TOCTOU (Time-of-check to time-of-use) vulnerability.
**Learning:** Using `tempfile.mktemp()` is deprecated and insecure because an attacker could create a malicious file or symlink at the generated path before the program opens it.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.close(fd)` or securely managed temporary directories/files instead.
