# RouteMesh threat model

## Assets

- Routing policy and demo backend behavior controls.
- Backend endpoint configuration and request/response metadata.
- Availability of the proxy under traffic and backend failures.

## Trust boundaries

- Clients are untrusted and reach the catch-all proxy and read-only observability API.
- Admin mutation endpoints are privileged and require `X-RouteMesh-Admin-Token`.
- Demo backends are isolated services in the Compose network; their behavior API is intended only for local experiments.
- Configuration is operator-controlled YAML and environment variables.

## Controls

- Startup refuses missing, short, or known example admin tokens.
- Admin tokens are compared with constant-time comparison and must be provided as secrets by the operator.
- Request body size is bounded; hop-by-hop headers are removed; redirects are not followed.
- Retries are limited to safe methods or idempotency-key requests and a shared retry budget.
- Routing inputs are validated; unknown policy names and backend IDs fail explicitly.
- Backend drain/resume controls require the admin token; draining prevents new selections while existing requests finish.
- Circuit recovery delays increase exponentially up to a configured maximum after failed probes.
- Request IDs are bounded and excluded from Prometheus labels.

## Known limits

- This learning service does not terminate TLS, authenticate users, or provide distributed admin authorization.
- Slow-start, TLS, HTTP/2, WebSocket forwarding, streaming request bodies, and dynamic service discovery are not implemented yet.
- The demo backend behavior API has no separate credential because it is meant for a private local Compose network. Do not expose those services publicly.
- Registry, circuit-breaker, bandit posterior, and decision stream state are process-local and reset on restart.
- Configure TLS and network policy at a trusted ingress before exposing a deployment. Do not treat this demo as a production edge proxy.
