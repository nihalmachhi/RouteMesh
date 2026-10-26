"""Deterministic behavior controls used by policy failure scenarios."""

import pytest

from routemesh.test_backends.behavior import BehaviorState


@pytest.mark.asyncio
async def test_flapping_behavior_fails_every_nth_request_and_resets_on_reconfigure():
    state = BehaviorState()
    await state.update({"flap_every": 3})
    failures = []
    for _ in range(6):
        _, failed = await state.begin_request()
        failures.append(failed)
    assert failures == [False, False, True, False, False, True]

    await state.update({"flap_every": 2})
    _, failed = await state.begin_request()
    assert not failed
