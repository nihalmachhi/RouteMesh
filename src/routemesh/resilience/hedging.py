"""Bounded safe-request hedging primitives."""

import asyncio
from collections.abc import Callable, Coroutine


async def hedge[T](
    primary: Callable[[], Coroutine[object, object, T]],
    secondary: Callable[[], Coroutine[object, object, T]],
    delay_seconds: float,
) -> T:
    """Start a backup after a delay, return the first result, cancel the loser."""
    if delay_seconds < 0:
        raise ValueError("hedge delay must be non-negative")
    first = asyncio.create_task(primary())
    try:
        done, _ = await asyncio.wait({first}, timeout=delay_seconds)
        if done:
            return await first
        second = asyncio.create_task(secondary())
        try:
            done, pending = await asyncio.wait({first, second}, return_when=asyncio.FIRST_COMPLETED)
            winner = next(iter(done))
            result = await winner
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            return result
        finally:
            if not second.done():
                second.cancel()
                await asyncio.gather(second, return_exceptions=True)
    finally:
        if not first.done():
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
