"""Sliding-window limiter behaviour with a controllable clock."""

import pytest

from app.core.exceptions import RateLimitedError
from app.core.rate_limit import RateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_limit_then_blocks_with_retry_after() -> None:
    clock = Clock()
    limiter = RateLimiter(max_calls=2, window_seconds=60, clock=clock)
    limiter.check("a")
    limiter.check("a")
    with pytest.raises(RateLimitedError) as info:
        limiter.check("a")
    assert info.value.headers == {"Retry-After": "60"}


def test_window_slides() -> None:
    clock = Clock()
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=clock)
    limiter.check("a")
    clock.now += 60
    limiter.check("a")  # old hit expired


def test_keys_are_independent() -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=Clock())
    limiter.check("a")
    limiter.check("b")
