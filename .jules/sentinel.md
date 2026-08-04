## 2024-05-24 - Predictable Temp File in Updater
**Vulnerability:** The Windows update process wrote a batch file to a predictable path (`tempfile.gettempdir() / "noveltrad_updater.bat"`) without randomized naming.
**Learning:** Hardcoded or predictable temp file paths are vulnerable to Time-of-Check to Time-of-Use (TOCTOU) attacks, allowing local privilege escalation if an attacker pre-creates the file.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.fdopen()` to securely create temporary files with random names and restricted permissions.
