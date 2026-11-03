# Changelog

Notable RouteMesh changes, with fixes documented only when covered by regression tests.

## [0.2.0] - 2026-11-03

### Fixed

- **P0-1:** stream compressed upstream bytes without relabeling decoded content (`test_forwarder_preserves_gzip_wire_bytes_and_encoding_headers`).
- **P0-2:** preserve repeated response headers such as `Set-Cookie` (`test_forwarder_preserves_query_body_and_request_id`).
- **P0-3:** stream request and response bodies, reject an over-limit upload while reading, and return 501 for WebSocket upgrades (`test_forwarder_streams_request_and_rejects_body_over_limit`, `test_proxy_routes_records_explanation_and_tracks_download_until_stream_end`).
- **P0-4:** expire unused retry credit on an injected-clock window (`test_retry_budget_expires_tokens_after_quiet_failure_period`).
- **P0-5:** fail closed without an admin token and serve operations routes on a distinct listener (`test_admin_reads_and_writes_fail_closed_without_token`, `test_proxy_health_and_metrics_endpoints_are_available`).
- **P1-1:** keep backend-reported load separate from proxy-measured in-flight counts (`test_health_checker_records_reported_load_separately`).
- **P1-2:** release half-open probe reservations and account for upstream HTTP errors (`test_abandoned_half_open_probe_releases_its_reservation`).
- **P1-3:** return the last upstream 5xx response when a retry cannot select another backend (`test_retry_returns_first_upstream_5xx_when_no_alternate_is_healthy`).
- **P1-4:** use bounded latency signals, stale-sample decay, and missing-weight defaults (`test_latency_signal_uses_a_stable_scale_instead_of_per_request_minmax`, `test_stale_latency_sample_decays_toward_neutral_prior`).
- **P1-5:** discard untrusted forwarding chains and validate request IDs (`test_forwarder_preserves_query_body_and_request_id`, `test_request_id_preserves_bounded_safe_values`).
- **P1-6:** apply a total upstream deadline, including response streaming, and cap global/per-backend concurrency (`test_forwarder_enforces_total_deadline_while_streaming_response`, `test_limit_admits_to_capacity_and_releases`, `test_global_admission_slot_is_held_until_stream_body_finishes`).
- **P2-1:** keep Prometheus counters and gauges cumulative across local observation resets (`test_proxy_routes_records_explanation_and_tracks_download_until_stream_end`).

### Added

- MIT license, security policy, CI/dependency automation, repository documentation, and hardened multi-stage Docker configuration.
- P2C and weighted round-robin routing, runtime bandit routing, adaptive concurrency control, outlier ejection, and opt-in `GET`/`HEAD` hedging (`test_enabled_hedge_returns_fast_alternate_and_cancels_slow_primary`).
- Seeded simulator, synthetic comparison report, offline weight search, service-graph analysis, bounded log-template mining, path normalization, and decision narration.
- A RouteMesh project site with an interactive simulator, reduced-motion-aware walkthrough, generated results, and Python-to-TypeScript parity fixtures.

### Decisions

- Computer vision stays excluded because HTTP routing has no image-understanding input.
- Metrics and admin reads/writes require a configured token. Compose publishes the operations listener only on host loopback.
- Simulator, tuner, and graph results are synthetic generated evidence, not production measurements.
