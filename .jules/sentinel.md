## 2026-06-16 - [Add Security Headers to Backend]
**Vulnerability:** The FastAPI backend lacked basic security headers like `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, and `Content-Security-Policy`. This could leave the application open to various web-based attacks (e.g. clickjacking, cross-site scripting) if the API is exposed or integrated into broader contexts.
**Learning:** Even internal or local desktop-bound APIs should adopt defense-in-depth measures. Implementing a simple middleware in `src/backend/server.py` efficiently secures all routes without requiring per-route modifications.
**Prevention:** Include security headers middleware by default when initializing any FastAPI app to establish a secure baseline.
