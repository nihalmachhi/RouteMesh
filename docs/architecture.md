# RouteMesh architecture

RouteMesh is a single-process, application-level HTTP reverse proxy intended as a learning and demonstration project. It reads backend definitions and routing settings from `configs/routemesh.yaml`, probes configured health endpoints, chooses an eligible backend, forwards requests, and records the selection reason.

## Request lifecycle

1. The FastAPI catch-all route creates or validates a bounded request ID and acquires an in-flight slot.
2. The router excludes unhealthy backends and those whose circuit breaker is open. A half-open backend receives only the configured recovery probes.
3. The active policy ranks the remaining backend snapshots. The decision contains the selected backend and an explanation that is added to the bounded decision log and event stream.
4. The HTTPX forwarder strips hop-by-hop headers, applies the body-size limit, and sends the request to the selected backend.
5. The router updates latency EWMA, rolling errors, breaker state, in-flight counts, and Prometheus metrics. Retry attempts are limited to safe methods or requests carrying an idempotency key, and consume a finite token budget.

## Boundaries

Backend health, routing telemetry, breakers, and the SSE event stream are held in process memory. Run one proxy process for the demo. The configured token protects all admin endpoints, including read-only views. Admin requests fail closed when no token is configured.

The proxy buffers request bodies up to `ROUTEMESH_MAX_BODY_BYTES`; streaming uploads, response streaming, TLS termination, HTTP/2, WebSockets, distributed state, and dynamic cloud discovery are not implemented. A routing score is an explicit heuristic, not a learned model. The benchmark scripts create local measurements; example values in the website are simulations and should not be presented as production results.

## Repository map

- `src/routemesh/proxy`: FastAPI app, routing/retries, request forwarding, backpressure, and admin API.
- `src/routemesh/policies`: round-robin, least-connections, and latency-aware policies.
- `src/routemesh/discovery`: YAML loading and in-memory backend registry.
- `src/routemesh/health`: active health checks and circuit breaker.
- `src/routemesh/metrics`: Prometheus metrics, EWMA, rolling windows, bounded decision log, and SSE.
- `src/routemesh/test_backends`: controllable demo backends.
- `src/routemesh/benchmarks`: Locust scenarios and report generation.
- `site`: GitHub Pages project site and interactive routing simulator.
- `tests`: unit and integration tests.
