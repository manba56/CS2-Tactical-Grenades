"""Simple in-memory rate limiter — no external dependencies."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import RLock


class RateLimiter:
    """Track request counts per key (IP) with a sliding window."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = RLock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune expired entries
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.pop(0)

            if len(hits) >= self.max_requests:
                return False

            hits.append(now)

            # Periodic cleanup: sweep empty buckets
            if len(self._hits) > 10000:
                self._hits = defaultdict(list, {
                    k: v for k, v in self._hits.items() if v
                })

            return True


# Default: 120 requests per minute per IP
_limiter = RateLimiter(max_requests=120, window_seconds=60)

# Stricter limits for auth endpoints
_auth_limiter = RateLimiter(max_requests=10, window_seconds=60)


def check_rate_limit(ip: str, strict: bool = False) -> bool:
    """Return True if the request is allowed. strict=True uses 10/min limit."""
    if strict:
        return _auth_limiter.is_allowed(ip)
    return _limiter.is_allowed(ip)


def get_client_ip(request) -> str:
    """Extract the real client IP, accounting for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host or "127.0.0.1"
    return "127.0.0.1"
