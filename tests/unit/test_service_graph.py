import pytest

from routemesh.graph.topology import ServiceEdge, ServiceGraph


def sample_graph():
    return ServiceGraph(
        {"client", "gateway", "profile", "orders", "inventory"},
        [
            ServiceEdge("client", "gateway", retries=1, latency_ms=5),
            ServiceEdge("gateway", "profile", retries=2, latency_ms=20),
            ServiceEdge("gateway", "orders", retries=0, latency_ms=10, locality_cost=20),
            ServiceEdge("orders", "inventory", retries=1, latency_ms=40),
        ],
    )


def test_service_graph_rejects_cycles_and_unknown_nodes():
    with pytest.raises(ValueError, match="cycle"):
        ServiceGraph({"a", "b"}, [ServiceEdge("a", "b"), ServiceEdge("b", "a")])
    with pytest.raises(ValueError, match="unknown node"):
        ServiceGraph({"a"}, [ServiceEdge("a", "b")])


def test_graph_reports_retry_amplification_and_failure_blast_radius():
    graph = sample_graph()
    assert graph.retry_amplification("client") == 6
    assert graph.blast_radius("inventory") == ("client", "gateway", "inventory", "orders")


def test_graph_reports_critical_latency_and_minimum_locality_cost_path():
    graph = sample_graph()
    assert graph.critical_path_ms("client", "inventory") == 55
    assert graph.min_cost_path("client", "inventory") == (
        "client",
        "gateway",
        "orders",
        "inventory",
    )
    assert graph.min_cost_path("client", "profile") == ("client", "gateway", "profile")


def test_graph_rejects_invalid_weights_and_unreachable_paths():
    graph = sample_graph()
    with pytest.raises(ValueError, match="non-negative"):
        graph.min_cost_path("client", "profile", latency_weight=-1)
    with pytest.raises(ValueError, match="unreachable"):
        graph.critical_path_ms("profile", "inventory")
