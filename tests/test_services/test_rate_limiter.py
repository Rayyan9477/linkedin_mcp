"""Tests for AsyncRateLimiter."""

import asyncio
import pytest

from linkedin_mcp.services.rate_limiter import AsyncRateLimiter


@pytest.mark.asyncio
async def test_basic_acquire():
    limiter = AsyncRateLimiter(calls_per_minute=60)
    # Should not block for a few calls
    for _ in range(3):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_allows_burst():
    limiter = AsyncRateLimiter(calls_per_minute=120)
    # Should allow burst up to token count
    for _ in range(5):
        await limiter.acquire()
