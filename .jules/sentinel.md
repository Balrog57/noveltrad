## 2024-05-14 - Fix Path Traversal Bypass via Backslash on POSIX
**Vulnerability:** PathValidator.validate_filename used os.path.basename to check for directory traversal but failed to normalize backslashes. On POSIX systems, os.path.basename does not recognize backslashes as path separators, allowing malicious paths like ..\..\etc\passwd to bypass the check.
**Learning:** Always normalize backslashes to forward slashes before validating paths with os.path.basename on cross-platform applications to avoid OS-specific bypasses.
**Prevention:** Ensure filenames are normalized by replacing '\' with '/' before checking with os.path.basename.
