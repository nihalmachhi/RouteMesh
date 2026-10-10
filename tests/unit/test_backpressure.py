import pytest

from routemesh.proxy.backpressure import BackpressureLimiter, Overloaded


@pytest.mark.asyncio
async def test_limiter_rejects_over_capacity_and_releases_slots():
    limiter = BackpressureLimiter(1)
    async with limiter.slot():
        with pytest.raises(Overloaded):
            async with limiter.slot():
                pass
    assert limiter.active == 0
