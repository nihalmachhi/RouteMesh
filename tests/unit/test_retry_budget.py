from routemesh.proxy.router import RetryBudget


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value


def test_retry_budget_caps_retries_to_fraction_of_original_requests():
    budget = RetryBudget(0.25)
    for _ in range(4):
        budget.start_request()
    assert budget.consume()
    assert not budget.consume()


def test_retry_budget_does_not_bank_unlimited_retries():
    budget = RetryBudget(0.1)
    for _ in range(10_000):
        budget.start_request()
    assert sum(budget.consume() for _ in range(100)) == 10
    assert not budget.consume()


def test_retry_budget_reset_discards_saved_tokens():
    budget = RetryBudget(0.5)
    budget.start_request()
    budget.start_request()
    budget.reset()
    assert not budget.consume()


def test_retry_budget_expires_tokens_after_quiet_failure_period():
    clock = FakeClock()
    budget = RetryBudget(0.1, clock=clock, token_ttl_seconds=5)
    for _ in range(10):
        budget.start_request()
    assert budget.consume()
    for _ in range(10):
        budget.start_request()
    assert budget.consume()
    clock.value += 6
    assert not budget.consume()
