from routemesh.proxy.router import RetryBudget


def test_retry_budget_caps_retries_to_fraction_of_original_requests():
    budget = RetryBudget(0.25)
    for _ in range(4):
        budget.start_request()
    assert budget.consume()
    assert not budget.consume()
