## 2024-05-18 - Overly Permissive CORS Middleware
**Vulnerability:** In `src/backend/server.py`, `CORSMiddleware` was configured with `allow_origins=["*"]` along with `allow_credentials=True`.
**Learning:** Using a wildcard for origins when credentials are allowed is prohibited by CORS standards as it allows any site to perform authenticated requests, leading to Cross-Site Request Forgery (CSRF). Since NovelTrad is a local app, allowing all origins is unnecessary and opens up the local API to malicious sites the user visits.
**Prevention:** Restrict `allow_origins` to loopback interfaces (`http://localhost`, `http://127.0.0.1`) for local applications.
