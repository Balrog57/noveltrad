# Sentinel Security Journal

Critical security learnings for this codebase. Routine fixes are not logged here.

## 2026-09-09 - Path Validation Consistency
**Vulnerability:** Inconsistent use of custom path validators (like `PathValidator.validate_filename()`) versus standard framework sanitizers (like Werkzeug's `secure_filename()`) can lead to path traversal bypass risks if custom architectural validators are bypassed or ignored.
**Learning:** Always apply the project's custom security validators consistently across all endpoints handling file paths or uploads, rather than relying solely on standard framework sanitizers, to prevent path traversal bypass risks.
**Prevention:** Ensure that custom architectural validators like `PathValidator` are systematically applied to all path or upload-handling endpoints.
