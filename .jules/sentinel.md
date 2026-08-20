## 2024-05-24 - Secure Temporary File Creation
**Vulnerability:** Use of deprecated `tempfile.mktemp()` creates TOCTOU (Time-of-Check to Time-of-Use) vulnerabilities by returning a predictable, non-existent path that an attacker could create before the application does.
**Learning:** Python's `mktemp()` is explicitly unsafe. When an application only needs a secure path to pass to another library (like `zipfile.ZipFile`), it's easy to mistakenly use `mktemp()`.
**Prevention:** Always use `fd, path = tempfile.mkstemp()` and immediately close the file descriptor with `os.close(fd)` if only the path is needed. This ensures the file is created securely with restricted permissions and no race condition.
## 2024-05-24 - Security Code Pattern (Path Validation)
**Vulnerability:** In `PathValidator.validate_filename`, `os.path.basename` on POSIX systems does not recognize backslashes (`\`) as path separators, allowing malicious filenames like `foo\bar.txt` to bypass validation.
**Learning:** Path parsing behavior differs between operating systems. `os.path.basename` relies on `os.path.sep`, which is only `/` on POSIX, meaning backslashes are treated as regular characters. This can lead to path traversal vulnerabilities if the file is later processed on or sent to a Windows system.
**Prevention:** Always normalize backslashes to forward slashes (e.g., `filename.replace('\\', '/')`) before calling `os.path.basename` when validating filenames for cross-platform security.
