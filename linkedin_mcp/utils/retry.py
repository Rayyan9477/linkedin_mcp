"""
Retry utilities for handling transient failures in API calls.

This module provides decorators and utilities for implementing automatic retries
with exponential backoff for operations that might fail temporarily.
"""

import asyncio
import functools
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from pydantic import BaseModel

logger = logging.getLogger("linkedin-mcp.retry")

# Type variables for generic function return types
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        self.last_exception = last_exception
        super().__init__(message)

class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 0.5
    max_delay: float = 60.0
    jitter: float = 0.1
    exponential_base: float = 2.0
    max_elapsed_time: Optional[float] = 300.0  # 5 minutes
    retry_on: Set[Type[Exception]] = frozenset({Exception})
    
    class Config:
        frozen = True
        json_encoders = {
            type: lambda v: f"{v.__module__}.{v.__name__}"
        }

def retry(
    func: Optional[F] = None,
    *,
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 60.0,
    jitter: float = 0.1,
    exponential_base: float = 2.0,
    max_elapsed_time: Optional[float] = 300.0,
    retry_on: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
) -> Union[F, Callable[[F], F]]:
    """
    Decorator that retries the wrapped function with exponential backoff.
    
    Args:
        func: The function to decorate (for direct usage as @retry)
        max_attempts: Maximum number of retry attempts (including initial attempt)
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter: Random jitter factor (0-1)
        exponential_base: Base for exponential backoff calculation
        max_elapsed_time: Maximum total time to spend retrying in seconds
        retry_on: Exception type(s) to retry on
        
    Returns:
        A decorator that applies retry logic to the wrapped function
    """
    # Allow using either @retry or @retry(...)
    if func is None:
        return cast(F, functools.partial(
            retry,
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            jitter=jitter,
            exponential_base=exponential_base,
            max_elapsed_time=max_elapsed_time,
            retry_on=retry_on
        ))
    
    # Convert single exception type to a tuple
    if isinstance(retry_on, type) and issubclass(retry_on, Exception):
        retry_on = (retry_on,)
    
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        jitter=jitter,
        exponential_base=exponential_base,
        max_elapsed_time=max_elapsed_time,
        retry_on=set(retry_on)
    )
    
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _retry_async_operation(
                func, 
                config,
                *args, 
                **kwargs
            )
        return cast(F, async_wrapper)
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _retry_sync_operation(
                func, 
                config,
                *args, 
                **kwargs
            )
        return cast(F, sync_wrapper)

async def _retry_async_operation(
    func: Callable[..., Any],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Execute an async function with retry logic."""
    start_time = time.monotonic()
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            # Execute the function
            return await func(*args, **kwargs)
            
        except tuple(config.retry_on) as e:
            last_exception = e
            
            # Check if we've exceeded the maximum elapsed time
            elapsed = time.monotonic() - start_time
            if config.max_elapsed_time and elapsed >= config.max_elapsed_time:
                raise RetryError(
                    f"Exceeded maximum elapsed time ({config.max_elapsed_time:.1f}s)",
                    last_exception
                ) from e
            
            # Check if this was the last attempt
            if attempt >= config.max_attempts:
                raise RetryError(
                    f"All {config.max_attempts} attempts failed",
                    last_exception
                ) from e
            
            # Calculate backoff with exponential backoff and jitter
            backoff = min(
                config.initial_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay
            )
            
            # Add jitter
            if config.jitter > 0:
                jitter_amount = backoff * config.jitter
                backoff = random.uniform(
                    backoff - jitter_amount,
                    backoff + jitter_amount
                )
            
            # Log the retry
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed with {type(e).__name__}: {str(e)}. "
                f"Retrying in {backoff:.2f}s..."
            )
            
            # Wait before retrying
            await asyncio.sleep(backoff)
    
    # This should never be reached due to the attempt check above
    raise RetryError("Unexpected error in retry logic", last_exception)

def _retry_sync_operation(
    func: Callable[..., Any],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Execute a sync function with retry logic."""
    start_time = time.monotonic()
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            # Execute the function
            return func(*args, **kwargs)
            
        except tuple(config.retry_on) as e:
            last_exception = e
            
            # Check if we've exceeded the maximum elapsed time
            elapsed = time.monotonic() - start_time
            if config.max_elapsed_time and elapsed >= config.max_elapsed_time:
                raise RetryError(
                    f"Exceeded maximum elapsed time ({config.max_elapsed_time:.1f}s)",
                    last_exception
                ) from e
            
            # Check if this was the last attempt
            if attempt >= config.max_attempts:
                raise RetryError(
                    f"All {config.max_attempts} attempts failed",
                    last_exception
                ) from e
            
            # Calculate backoff with exponential backoff and jitter
            backoff = min(
                config.initial_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay
            )
            
            # Add jitter
            if config.jitter > 0:
                jitter_amount = backoff * config.jitter
                backoff = random.uniform(
                    backoff - jitter_amount,
                    backoff + jitter_amount
                )
            
            # Log the retry
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed with {type(e).__name__}: {str(e)}. "
                f"Retrying in {backoff:.2f}s..."
            )
            
            # Wait before retrying
            time.sleep(backoff)
    
    # This should never be reached due to the attempt check above
    raise RetryError("Unexpected error in retry logic", last_exception)

# Common retry configurations
DEFAULT_RETRY_CONFIG = RetryConfig()

# Retry configuration for network operations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    retry_on={
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    }
)

# Retry configuration for rate-limited operations
RATE_LIMIT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=5.0,
    max_delay=60.0,
    retry_on={
        Exception,  # Will be filtered by rate limiter
    }
)

# Retry configuration for login operations
LOGIN_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=2.0,
    max_delay=10.0,
    retry_on={
        ConnectionError,
        TimeoutError,
    }
)
