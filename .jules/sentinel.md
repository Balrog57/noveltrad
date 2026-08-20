## 2025-02-14 - [tempfile.mktemp TOCTOU Vulnerability]
**Vulnerability:** Found uses of tempfile.mktemp() which creates a Time-Of-Check to Time-Of-Use (TOCTOU) race condition because it returns a path without creating the file, allowing predictable temporary filenames to be hijacked by an attacker before the application creates the file.
**Learning:** Always create temporary files securely with proper permissions and random naming in a single atomic step.
**Prevention:** Use tempfile.mkstemp() combined with os.fdopen() to securely create temporary files and return an open file descriptor, avoiding the race condition.
