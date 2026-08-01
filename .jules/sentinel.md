## 2026-08-01 - Fix Predictable Temporary File Path (TOCTOU)
**Vulnerability:** Predictable temporary file path `noveltrad_updater.bat` created in the shared temporary directory.
**Learning:** `tempfile.gettempdir()` combined with a static filename allows attackers to pre-create the file or modify the batch script before execution.
**Prevention:** Always use `tempfile.mkstemp()` with `os.fdopen()` to create secure temporary files with randomized names and restricted permissions.
