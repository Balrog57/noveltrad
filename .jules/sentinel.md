## 2024-05-18 - Fix TOCTOU vulnerability in temp files
**Vulnerability:** Use of deprecated and insecure `tempfile.mktemp()` function.
**Learning:** `tempfile.mktemp()` returns a path that could be taken by an attacker before the application actually opens it, leading to a Time-Of-Check to Time-Of-Use vulnerability.
**Prevention:** Always use `tempfile.mkstemp()` which creates the file and returns a file descriptor and path safely, preventing interception.
