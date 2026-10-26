from routemesh.health.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def utc_now(self):
        raise NotImplementedError


def test_breaker_opens_then_closes_after_recovery_probes():
    clock = FakeClock()
    breaker = CircuitBreaker(
        consecutive_limit=2,
        open_seconds=5,
        recovery_successes=2,
        max_half_open_probes=1,
        clock=clock,
    )
    breaker.record(False)
    breaker.record(False)
    assert breaker.state == "open"
    assert not breaker.can_select()
    clock.value = 5
    assert breaker.allow_request()
    assert breaker.state == "half_open"
    breaker.record(True)
    assert breaker.allow_request()
    breaker.record(True)
    assert breaker.state == "closed"


def test_half_open_failure_reopens_breaker():
    clock = FakeClock()
    breaker = CircuitBreaker(
        consecutive_limit=1, open_seconds=1, max_open_seconds=4, clock=clock
    )
    breaker.record(False)
    clock.value = 1
    assert breaker.allow_request()
    breaker.record(False)
    assert breaker.state == "open"
    clock.value = 2.9
    assert not breaker.can_select()
    clock.value = 3
    assert breaker.can_select()
