from routemesh.health.outlier import OutlierDetector


def test_outlier_ejection_trips_and_expires():
    detector = OutlierDetector(window_size=5, minimum_requests=3, failure_threshold=0.6)
    assert not detector.record(False, 0)
    assert not detector.record(False, 1)
    assert detector.record(False, 2)
    assert detector.is_ejected(4)
    assert not detector.is_ejected(20)
