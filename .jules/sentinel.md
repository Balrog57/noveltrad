## 2025-02-14 - Fix TOCTOU vulnerability in updater batch script
**Vulnerability:** The application used `tempfile.gettempdir()` combined with a hardcoded filename (`noveltrad_updater.bat`) to create the updater script.
**Learning:** This approach is vulnerable to Time-Of-Check to Time-Of-Use (TOCTOU) and symlink attacks. An attacker could pre-create the file or a symlink with restrictive permissions or malicious content before the app writes to it, leading to arbitrary code execution or privilege escalation when the batch script is executed.
**Prevention:** Always use `tempfile.mkstemp()` to securely create temporary files with randomized names and restrictive permissions, and use `os.fdopen()` to write to the returned file descriptor safely.
