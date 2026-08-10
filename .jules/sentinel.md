## 2024-08-10 - Insecure temporary file creation (mktemp)
**Vulnerability:** Use of `tempfile.mktemp()` creates a predictable temporary file path, leading to TOCTOU (Time-of-Check to Time-of-Use) vulnerabilities where another process could hijack the file before it's used.
**Learning:** Legacy Python APIs like `mktemp` are insecure and can easily be overlooked.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.close(fd)` or `os.fdopen()`, or use `tempfile.NamedTemporaryFile(delete=False)`.
