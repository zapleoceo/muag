"""Concurrency limiter for the task queue — max N tasks running simultaneously."""
import asyncio
import logging

log = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_MAX_CONCURRENT = 3


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    return _semaphore


async def run_with_limit(coro) -> None:
    """Run a coroutine with the global concurrency limit."""
    sem = get_semaphore()
    async with sem:
        await coro
