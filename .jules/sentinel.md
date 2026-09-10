# Sentinel Security Journal

Critical security learnings for this codebase. Routine fixes are not logged here.

## 2026-09-10 - Enforce Consistent Custom Path Validation
**Vulnerability:** File upload and serve endpoints relied partially on Werkzeug's `secure_filename()` instead of consistently applying the project's custom `PathValidator.validate_filename()`.
**Learning:** Relying solely on framework sanitizers can lead to path traversal bypasses if the project architecture expects custom validators to handle edge cases.
**Prevention:** Always apply the project's custom security validators consistently across all endpoints handling file paths or uploads.
