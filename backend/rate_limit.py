import time
from collections import defaultdict
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests_per_minute: int = 120, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.max_requests_per_minute = max(1, int(max_requests_per_minute))
        self.requests_by_ip: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            timestamps = self.requests_by_ip[ip]
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if len(timestamps) >= self.max_requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please retry in a minute."},
                )
            timestamps.append(now)

        return await call_next(request)
