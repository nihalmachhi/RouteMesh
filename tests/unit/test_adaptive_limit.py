import pytest

from routemesh.resilience.adaptive_limit import AdaptiveConcurrencyLimit


@pytest.mark.asyncio
async def test_limit_admits_to_capacity_and_releases():
    limit = AdaptiveConcurrencyLimit(initial=2, maximum=4)
    await limit.acquire()
    await limit.acquire()
    assert limit.in_flight == 2
    await limit.release()
    assert limit.in_flight == 1


@pytest.mark.asyncio
async def test_limit_adds_capacity_when_healthy_and_decreases_on_congestion():
    limit = AdaptiveConcurrencyLimit(initial=10, maximum=20, target_latency_ms=100)
    assert await limit.observe(50, True) == 11
    assert await limit.observe(150, True) == 7
    assert await limit.observe(10, False) == 4


def test_limit_rejects_invalid_bounds():
    with pytest.raises(ValueError):
        AdaptiveConcurrencyLimit(minimum=5, maximum=2)
