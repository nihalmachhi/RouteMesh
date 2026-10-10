import pytest

from routemesh.metrics.ewma import Ewma
from routemesh.metrics.rolling_window import RollingWindow


def test_ewma_uses_alpha_for_new_sample():
    value = Ewma(alpha=0.2)
    assert value.update(100) == 100
    assert value.update(0) == pytest.approx(80)


def test_rolling_window_evicts_old_observations():
    window = RollingWindow(capacity=2)
    assert window.add(True) == 0
    assert window.add(False) == 0.5
    assert window.add(True) == 0.5


def test_ewma_rejects_invalid_alpha_and_negative_samples():
    with pytest.raises(ValueError):
        Ewma(alpha=0)
    with pytest.raises(ValueError):
        Ewma().update(-1)
