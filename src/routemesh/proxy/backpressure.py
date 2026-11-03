"""Non-blocking in-flight request admission limiter."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from routemesh.core.errors import RouteMeshError


class Overloaded(RouteMeshError):
    """Raised when the configured in-flight request limit is reached."""


class BackpressureLimiter:
    """Reject excess requests immediately instead of growing an unbounded queue."""

    def __init__(self, maximum: int) -> None:
        self._maximum = maximum
        self._active = 0
        self._lock = asyncio.Lock()

    @property
    def active(self) -> int:
        """Return the current admitted request count."""
        return self._active

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Reserve one slot or fail immediately with an overload signal."""
        await self.acquire()
        try:
            yield
        finally:
            await self.release()

    async def acquire(self) -> None:
        """Reserve one slot until its response body has finished streaming."""
        async with self._lock:
            if self._active >= self._maximum:
                raise Overloaded("RouteMesh is at its in-flight request limit")
            self._active += 1

    async def release(self) -> None:
        """Release an admitted request without allowing the count to underflow."""
        async with self._lock:
            self._active = max(0, self._active - 1)
