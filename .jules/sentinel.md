## 2026-07-23 - [Insecure Temporary Batch File Creation]
**Vulnerability:** The batch script used for auto-updating was created at a predictable path (`tempfile.gettempdir() / "noveltrad_updater.bat"`) without checking for pre-existence.
**Learning:** Predictable temporary file paths for executable scripts present a TOCTOU and hijacking risk in multi-user environments. Attackers can pre-create or modify the file before execution.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.fdopen()` to securely create temporary files with randomized names and restricted permissions (mode `0600`).
