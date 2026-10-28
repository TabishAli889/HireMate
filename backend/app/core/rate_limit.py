"""Small in-memory sliding-window rate limiter, used as a FastAPI dependency.

Good enough for a single-instance deployment. For multiple instances, swap for Redis.
"""

import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError


def client_key(request: Request) -> str:
    """Best-effort client id: first X-Forwarded-For hop (set by the Next proxy / Vercel), else socket IP."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Allows `max_calls` per `window_seconds` per client; raises RateLimitedError beyond that.

    `scope` groups several routes under one budget (e.g. all LLM analysis calls); without it,
    each URL path gets its own budget.
    """

    def __init__(
        self,
        max_calls: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        scope: str | None = None,
    ):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.scope = scope
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a hit for `key`, or raise if the limit is already reached."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_calls:
                retry_after = max(1, math.ceil(self.window_seconds - (now - hits[0])))
                raise RateLimitedError(
                    f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        """Forget all recorded hits (used by tests)."""
        with self._lock:
            self._hits.clear()

    def __call__(self, request: Request) -> None:
        self.check(f"{self.scope or request.url.path}:{client_key(request)}")


_settings = get_settings()
upload_limiter = RateLimiter(max_calls=_settings.upload_rate_limit_per_minute, window_seconds=60)
analysis_limiter = RateLimiter(max_calls=_settings.analysis_rate_limit_per_minute, window_seconds=60, scope="analysis")
