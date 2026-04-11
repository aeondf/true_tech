"""Simple in-process rate limiter (per IP). For production — use Redis."""
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

# {ip: [timestamp, ...]}
_windows: dict[str, list[float]] = defaultdict(list)
WINDOW = 60.0  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            ip = request.client.host if request.client else "unknown"
        except Exception:
            ip = "unknown"
        now = time.monotonic()

        hits = _windows[ip]
        _windows[ip] = [t for t in hits if now - t < WINDOW]

        if len(_windows[ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        _windows[ip].append(now)
        return await call_next(request)
