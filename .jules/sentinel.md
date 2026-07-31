
## 2026-07-31 - [Insecure Temporary File Creation in Updater]
**Vulnerability:** The application was creating an update batch script at a predictable path (`Path(tempfile.gettempdir()) / "noveltrad_updater.bat"`) using `write_text()`. This introduces a Time-Of-Check to Time-Of-Use (TOCTOU) vulnerability where an attacker could potentially hijack the file between creation and execution, or pre-create it with malicious content or restricted permissions.
**Learning:** Even internal utility scripts like updaters running in the background need secure file handling. Predictable temporary file paths in shared directories (like `%TEMP%`) are a common vector for local privilege escalation or arbitrary code execution.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.fdopen()` when creating temporary files, especially those that will be executed. This ensures securely randomized file names and appropriately restricted file permissions upon creation.
