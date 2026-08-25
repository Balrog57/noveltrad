## 2024-08-25 - Fix Path Traversal via os.path.basename on POSIX
**Vulnerability:** File uploads could bypass directory traversal checks using backslashes (e.g., 'evil\file.txt') because `os.path.basename` on POSIX systems does not recognize '\' as a path separator.
**Learning:** Relying solely on `os.path.basename` to strip path components is unsafe if the input string contains Windows-style backslashes and the server runs on a POSIX system. The backslashes will be treated as part of the filename, allowing files to be written outside the intended directory if later components use them as paths.
**Prevention:** Always normalize backslashes to forward slashes (e.g., `filename.replace('\', '/')`) before calling `os.path.basename` to validate or sanitize filenames.
