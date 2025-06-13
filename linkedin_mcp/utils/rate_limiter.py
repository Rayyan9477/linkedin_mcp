"""
Rate limiting and retry utilities for the LinkedIn MCP server.

This module provides decorators and utilities for implementing rate limiting
and automatic retries for LinkedIn API calls.
"""

import asyncio
import functools
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

from pydantic import BaseModel

logger = logging.getLogger("linkedin-mcp.rate_limiter")

# Type variable for generic function return types
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class RateLimitExceeded(Exception):
    """Raised when the rate limit has been exceeded."""
    def __init__(self, reset_time: float, limit: int, window: int):
        self.reset_time = reset_time
        self.limit = limit
        self.window = window
        self.retry_after = max(0, reset_time - time.time())
        super().__init__(
            f"Rate limit exceeded. Limit: {limit} requests per {window} seconds. "
            f"Reset in {self.retry_after:.1f} seconds."
        )

class RateLimiter:
    """
    A rate limiter that implements the token bucket algorithm.
    
    This class can be used as a decorator or as a context manager to limit
    the rate of operations.
    """
    
    def __init__(
        self, 
        max_requests: int, 
        window: int,
        retry_attempts: int = 3,
        initial_backoff: float = 0.5,
        max_backoff: float = 60.0,
        jitter: float = 0.1
    ):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            window: Time window in seconds
            retry_attempts: Number of retry attempts when rate limited
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            jitter: Jitter factor for backoff (0-1)
        """
        self.max_requests = max_requests
        self.window = window
        self.retry_attempts = retry_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.jitter = jitter
        
        # Track request timestamps
        self.requests: List[float] = []
        self.lock = asyncio.Lock()
    
    def _get_backoff_time(self, attempt: int) -> float:
        """Calculate backoff time with exponential backoff and jitter."""
        backoff = min(
            self.initial_backoff * (2 ** attempt),
            self.max_backoff
        )
        jitter_amount = backoff * self.jitter
        backoff += (2 * jitter_amount * (hash(str(attempt)) % 100) / 100) - jitter_amount
        return backoff
    
    def _cleanup_old_requests(self, now: float):
        """Remove requests older than the time window."""
        cutoff = now - self.window
        self.requests = [t for t in self.requests if t > cutoff]
    
    async def _acquire(self) -> float:
        """
        Acquire a token from the rate limiter.
        
        Returns:
            The timestamp when the request was made.
            
        Raises:
            RateLimitExceeded: If the rate limit has been exceeded.
        """
        async with self.lock:
            now = time.time()
            self._cleanup_old_requests(now)
            
            if len(self.requests) >= self.max_requests:
                # Calculate when we can make the next request
                oldest_request = self.requests[0]
                reset_time = oldest_request + self.window
                raise RateLimitExceeded(
                    reset_time=reset_time,
                    limit=self.max_requests,
                    window=self.window
                )
            
            # Add the current request
            self.requests.append(now)
            return now
    
    async def __call__(self, func: F) -> F:
        """
        Decorator to apply rate limiting to a function.
        
        Args:
            func: The function to decorate
            
        Returns:
            Decorated function with rate limiting applied
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.retry_attempts + 1):
                try:
                    # Try to acquire a token
                    timestamp = await self._acquire()
                    
                    # Call the wrapped function
                    return await func(*args, **kwargs)
                    
                except RateLimitExceeded as e:
                    last_exception = e
                    if attempt == self.retry_attempts:
                        break
                        
                    # Calculate backoff time
                    backoff = self._get_backoff_time(attempt)
                    logger.warning(
                        f"Rate limited. Attempt {attempt + 1}/{self.retry_attempts}. "
                        f"Retrying in {backoff:.2f}s..."
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(backoff)
            
            # If we get here, all retries failed
            raise last_exception
            
        return cast(F, wrapper)
    
    async def __aenter__(self):
        """Context manager entry."""
        await self._acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

def rate_limited(
    max_requests: int, 
    window: int,
    retry_attempts: int = 3,
    initial_backoff: float = 0.5,
    max_backoff: float = 60.0,
    jitter: float = 0.1
):
    """
    Decorator factory for rate limiting functions.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        window: Time window in seconds
        retry_attempts: Number of retry attempts when rate limited
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        jitter: Jitter factor for backoff (0-1)
        
    Returns:
        A decorator that applies rate limiting to the wrapped function
    """
    def decorator(func: F) -> F:
        limiter = RateLimiter(
            max_requests=max_requests,
            window=window,
            retry_attempts=retry_attempts,
            initial_backoff=initial_backoff,
            max_backoff=max_backoff,
            jitter=jitter
        )
        return limiter(func)
    return decorator

# Default rate limiter for LinkedIn API (30 requests per minute)
DEFAULT_LINKEDIN_RATE_LIMITER = RateLimiter(
    max_requests=30,
    window=60,  # 30 requests per minute
    retry_attempts=3
)

# Rate limiter for search operations (typically more restricted)
SEARCH_RATE_LIMITER = RateLimiter(
    max_requests=5,
    window=60,  # 5 requests per minute
    retry_attempts=3
)

# Rate limiter for login operations (very restricted)
LOGIN_RATE_LIMITER = RateLimiter(
    max_requests=3,
    window=300,  # 3 requests per 5 minutes
    retry_attempts=1
)
