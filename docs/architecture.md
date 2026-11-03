# RouteMesh architecture

RouteMesh is a single-process HTTP reverse proxy. It reads static backend definitions from `configs/routemesh.yaml`, probes their health, selects a healthy target, streams the request and response, and records the decision. It cannot forward to a client-selected URL.

## Request lifecycle

1. The proxy validates or creates a bounded request ID and applies global admission control.
2. The router filters unhealthy, open-circuit, and temporarily ejected backends. A policy selects among the remaining snapshots.
3. The decision and its reason are appended to a bounded decision log and an in-process event stream.
4. The HTTPX forwarder streams request and response bytes, enforces body and total-time limits, and preserves duplicate response headers.
5. The router updates latency EWMA, rolling errors, breaker and outlier state, metrics, and retry budget. When explicitly enabled, it can hedge a bodyless `GET` or `HEAD` after the configured delay; the duplicate consumes retry budget and is canceled when another attempt wins.

## Operations plane

The data path listens on port 8000. The operations ASGI app runs on a separate listener with admin routes, metrics, and liveness. Reads and writes require `X-RouteMesh-Admin-Token`; without a configured token these endpoints return 503. Local execution defaults to `127.0.0.1`. Compose binds the operations listener to the private container network and publishes it to host loopback only (`127.0.0.1:9000`). Prometheus uses the same bearer token to scrape metrics.

Health state, route decisions, event streams, breakers, outlier windows, retry credits, and adaptive limits are process-local. Run one proxy process for the demo. WebSockets, TLS termination, dynamic discovery, and distributed consistency are not implemented.

## Repository map

- `src/routemesh/proxy`: proxy app, router, streaming forwarder, and global admission control.
- `src/routemesh/admin`: separate operations app, authenticated reads and controls, and demo fault injection.
- `src/routemesh/policies`: round-robin, least-connections, latency-aware, P2C, and weighted round-robin.
- `src/routemesh/health`: active checks, circuit breaker, and rolling outlier ejection.
- `src/routemesh/resilience`: adaptive per-backend concurrency and a bounded hedge primitive.
- `src/routemesh/graph`: validated DAG analysis, retry amplification, blast radius, and path costs.
- `src/routemesh/logmining` and `src/routemesh/explain`: deterministic templates, path labels, and decision narration.
- `src/routemesh/sim`: seeded synthetic workloads, comparison reports, and offline weight search.
- `site`: project site and TypeScript simulator checked against Python fixtures.
- `benchmarks`: Locust workload for local proxy measurements.
