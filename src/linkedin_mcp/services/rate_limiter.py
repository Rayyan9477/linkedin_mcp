"""Simple async rate limiter using token bucket algorithm."""

import asyncio
import time


class AsyncRateLimiter:
    """Token bucket rate limiter for async code."""

    def __init__(self, calls_per_minute: int = 30):
        self._rate = calls_per_minute
        self._tokens = float(calls_per_minute)
        self._max_tokens = float(calls_per_minute)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a rate limit token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._max_tokens, self._tokens + elapsed * (self._rate / 60.0))
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / (self._rate / 60.0)
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0
