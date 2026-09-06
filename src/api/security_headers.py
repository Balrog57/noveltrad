"""
Baseline HTTP security headers for the local web UI.

The SPA is same-origin and already gated by a per-session API token (issue
#210), but these headers add defense in depth: they limit MIME sniffing,
clickjacking, referrer leakage, and access to browser features the app never
uses.
"""


def apply_security_headers(response):
    """Attach standard security headers to an outgoing Flask response."""
    # Prevent browsers from MIME-sniffing away from declared Content-Type.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # The UI is not designed to be embedded in third-party frames.
    response.headers.setdefault("X-Frame-Options", "DENY")
    # Avoid leaking full URLs (which may carry ?token= on download links).
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # The translation UI does not need these privileged APIs.
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )
    return response
