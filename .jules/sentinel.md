# Sentinel Security Journal

Critical security learnings for this codebase. Routine fixes are not logged here.

## 2026-09-08 - Inconsistent Path Validation in Uploads
**Vulnerability:** The voice prompt upload endpoint relied solely on `secure_filename()` instead of using the custom `PathValidator.validate_filename()` like other endpoints, creating a potential path traversal bypass risk if `secure_filename()`'s behavior deviates from expected security policies.
**Learning:** Standard library or framework sanitizers (like `secure_filename()`) should not bypass or replace custom security validators built for the specific architecture unless explicitly designed to do so. Inconsistent validation logic creates attack surfaces.
**Prevention:** Always consistently apply standard, custom security components (`PathValidator`) across all similar endpoints (like file uploads) rather than falling back to generic framework functions.
