## 2024-05-30 - [Strict Filename Validation]
**Vulnerability:** The TTS route `delete_voice_prompt` used `werkzeug.utils.secure_filename` on user-supplied filenames before deletion. `secure_filename` mangles invalid paths (e.g., stripping path separators) instead of rejecting them, which could lead to deleting unintended files (e.g., `foo\bar.txt` gets mangled to `foobar.txt`).
**Learning:** Using sanitization functions (`secure_filename`) for validation is dangerous. Sanitization changes the input to make it safe, which can change the target of an operation unexpectedly.
**Prevention:** Always use strict validation (like `PathValidator.validate_filename`) that explicitly rejects malformed inputs with an error, rather than silently mangling them.
