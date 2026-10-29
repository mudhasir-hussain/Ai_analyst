import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from core.config import settings

logger = logging.getLogger("ai_analyst_backend.rate_limiter")


class InMemoryRateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Tracks client request timestamps within a 60-second window, keyed by
    client identifier (Bearer token or client IP address) and bucket type.
    """
    def __init__(self):
        # Maps (client_key, bucket_type) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self, current_time: float):
        """Purges stale records older than 60 seconds every 30 seconds."""
        if current_time - self._last_cleanup < 30.0:
            return
        self._last_cleanup = current_time
        cutoff = current_time - 60.0
        keys_to_delete = []
        for key, timestamps in self._history.items():
            valid = [t for t in timestamps if t > cutoff]
            if valid:
                self._history[key] = valid
            else:
                keys_to_delete.append(key)
        for k in keys_to_delete:
            del self._history[k]

    def is_allowed(self, client_key: str, bucket_type: str, limit_per_minute: int) -> Tuple[bool, int, int]:
        """
        Determines if an incoming request is allowed under the sliding window limit.
        Returns:
            Tuple[bool, int, int]: (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        self._cleanup_old_entries(now)
        cutoff = now - 60.0

        key = (client_key, bucket_type)
        timestamps = [t for t in self._history[key] if t > cutoff]
        self._history[key] = timestamps

        if len(timestamps) >= limit_per_minute:
            oldest = timestamps[0]
            retry_after = max(1, int(60.0 - (now - oldest)))
            return False, 0, retry_after

        # Record this request
        self._history[key].append(now)
        remaining = max(0, limit_per_minute - len(self._history[key]))
        return True, remaining, 0

    def reset(self):
        """Resets the rate limiter cache (useful for testing)."""
        self._history.clear()


limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette Middleware enforcing rate limits on incoming HTTP requests.
    Exempts static assets, documentation, and system health check pings.
    """
    async def dispatch(self, request: Request, call_next):
        if not getattr(settings, "ENABLE_RATE_LIMIT", True):
            return await call_next(request)

        path = request.url.path

        # 1. Exempt health checks, interactive documentation, and static files
        if path in {"/health", "/docs", "/redoc", "/openapi.json"} or path.startswith("/assets"):
            return await call_next(request)

        # 2. Extract Client Key (Bearer token if authenticated, else client IP)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            client_id = auth_header[7:].strip()
        else:
            client_id = request.client.host if request.client else "127.0.0.1"

        # 3. Classify Request into Rate Limit Buckets
        # Heavy endpoints: AI planner, Analytical Q&A, Auto-Heal, ML training/benchmarks, reports
        is_heavy = any(h in path for h in [
            "/ai/plan",
            "/ai/ask",
            "/ai/auto-heal",
            "/ml/train",
            "/ml/compare",
            "/reports"
        ])

        if is_heavy:
            bucket = "heavy_ai_ml"
            limit = getattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 30)
        else:
            bucket = "general"
            limit = getattr(settings, "DEFAULT_RATE_LIMIT_PER_MINUTE", 120)

        # 4. Check Rate Limit
        allowed, remaining, retry_after = limiter.is_allowed(client_id, bucket, limit)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for client '{client_id[:16]}' on '{path}' "
                f"[bucket={bucket}, limit={limit}/min]"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded for {bucket}. Limit is {limit} requests per minute. Please try again in {retry_after}s.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0"
                }
            )

        # 5. Process Request and inject rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
