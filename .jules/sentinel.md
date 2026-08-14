## YYYY-MM-DD - [Title]
**Vulnerability:** [Details]
**Learning:** [Insight]
**Prevention:** [Action]
## 2025-01-20 - Fix TOCTOU vulnerability in temporary file creation
**Vulnerability:** Use of deprecated `tempfile.mktemp()` in EPUB reconstruction which causes Time-Of-Check to Time-Of-Use (TOCTOU) vulnerability due to predictable path generation.
**Learning:** The codebase relies on `mktemp()` to get a file path for `zipfile.ZipFile` to write to, missing the fact that `mktemp()` is inherently insecure.
**Prevention:** Always use `tempfile.mkstemp()` and safely close the file descriptor `os.close(fd)` if only the secure path is needed.
## 2025-01-20 - Fix Path Traversal bypass in PathValidator
**Vulnerability:** Use of `os.path.basename` on POSIX systems to validate filenames allows backslash path separators (e.g., `foo\bar.txt`) to bypass the check, potentially enabling path traversal.
**Learning:** `os.path.basename` relies on the system's `os.path.sep`, which is only `/` on POSIX systems. Backslashes are not treated as separators, leading to validation bypass.
**Prevention:** Normalize backslashes to forward slashes before calling `os.path.basename` to ensure uniform behavior across platforms.
