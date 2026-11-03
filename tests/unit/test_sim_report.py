from routemesh.sim.report import build_report


def test_report_includes_generated_policy_tuning_and_graph_evidence():
    report = build_report()
    assert report["scenario_count"] == 3
    assert report["seed_count"] == 20
    assert report["tuning"]["candidate_count"] == 20
    assert report["retry_amplification"]["maximum_attempts_per_downstream_call"] == 12
    assert report["bandit_evaluation"]["rounds"] == 200
    assert report["nlp_evaluation"]["input_lines"] == 4
    assert "synthetic" in report["limitations"].lower()
