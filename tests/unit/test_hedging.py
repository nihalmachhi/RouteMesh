import asyncio

import pytest

from routemesh.resilience.hedging import hedge


@pytest.mark.asyncio
async def test_fast_primary_avoids_starting_backup():
    started = False

    async def backup():
        nonlocal started
        started = True
        return "backup"

    assert await hedge(lambda: asyncio.sleep(0, result="primary"), backup, 0.1) == "primary"
    assert not started


@pytest.mark.asyncio
async def test_backup_wins_after_slow_primary():
    async def primary():
        await asyncio.sleep(1)
        return "primary"

    assert await hedge(primary, lambda: asyncio.sleep(0, result="backup"), 0.001) == "backup"
