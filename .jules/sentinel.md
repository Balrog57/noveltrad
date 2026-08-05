
## 2025-02-12 - Secure Temporary File Creation
**Vulnerability:** Predictable temporary file path in updater (`noveltrad_updater.bat`) created via `tempfile.gettempdir()`, susceptible to TOCTOU and hijacking.
**Learning:** Shared temporary directories require randomized file names and restricted permissions when creating executable scripts.
**Prevention:** Always use `tempfile.mkstemp()` combined with `os.fdopen()` to securely create temporary files instead of `tempfile.gettempdir()`.
