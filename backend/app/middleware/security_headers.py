from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# The interactive API docs (dev only; disabled in production) load Swagger UI
# assets, which a 'default-src none' CSP would block.
DOCS_PATHS = ("/docs", "/redoc")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
        # This API serves JSON only — nothing should ever execute or embed it.
        if not request.url.path.startswith(DOCS_PATHS):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
