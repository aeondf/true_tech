"""Exponential backoff retry decorator for async functions."""
import asyncio
import functools
import httpx


def with_retry(retries: int = 3, retry_on: set[int] = frozenset({429, 503})):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await fn(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code not in retry_on or attempt == retries - 1:
                        raise
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
        return wrapper
    return decorator
