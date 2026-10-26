# Benchmark results

Measured RouteMesh policy comparison. Raw Locust CSV and the p95 chart are in output/benchmarks/20261026T062007Z.

## Conditions

- scenarios: {'slow': {'latency_ms': 180, 'jitter_ms': 0, 'error_rate': 0.0, 'cpu_percent': 90, 'down': False, 'flap_every': 0}, 'failing': {'latency_ms': 10, 'jitter_ms': 0, 'error_rate': 0.35, 'cpu_percent': 75, 'down': False, 'flap_every': 0}, 'flapping': {'latency_ms': 15, 'jitter_ms': 0, 'error_rate': 0.0, 'cpu_percent': 70, 'down': False, 'flap_every': 4}}
- users: 30
- ramp_users_per_second: 5
- duration_per_policy: 10s
- telemetry_reset_each_policy: yes
- locust_seed: not applicable; fixed workload has no randomized user actions
- machine: Windows-11-10.0.26200-SP0
- generated_at_utc: 20261026T062007Z
- commit: 148cc20ec88aed6fab7f27b2a5fbad87939654db
- working_tree_dirty: true (the benchmark included the uncommitted policy and harness changes at this revision)

Errors count final HTTP failures observed by Locust after RouteMesh retries. The 0% values here do not mean the injected backend errors never occurred; successful retries can hide an upstream attempt failure from the client.

| Scenario | Policy | Requests | Errors | Error rate | req/s | p50 ms | p95 ms | p99 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slow | round_robin | 2574 | 0 | 0.0000 | 285.44 | 18.00 | 210.00 | 210.00 |
| slow | least_connections | 2406 | 0 | 0.0000 | 266.80 | 54.00 | 240.00 | 300.00 |
| slow | power_of_two_choices | 2564 | 0 | 0.0000 | 284.54 | 50.00 | 240.00 | 290.00 |
| slow | ewma_latency | 1979 | 0 | 0.0000 | 219.27 | 66.00 | 290.00 | 450.00 |
| slow | latency_aware | 2084 | 0 | 0.0000 | 231.08 | 67.00 | 260.00 | 390.00 |
| slow | thompson_sampling | 2299 | 0 | 0.0000 | 254.98 | 54.00 | 260.00 | 380.00 |
| failing | round_robin | 2432 | 0 | 0.0000 | 269.85 | 56.00 | 220.00 | 340.00 |
| failing | least_connections | 2467 | 0 | 0.0000 | 273.65 | 55.00 | 230.00 | 350.00 |
| failing | power_of_two_choices | 2404 | 0 | 0.0000 | 266.66 | 57.00 | 240.00 | 350.00 |
| failing | ewma_latency | 1984 | 0 | 0.0000 | 219.79 | 66.00 | 300.00 | 480.00 |
| failing | latency_aware | 2124 | 0 | 0.0000 | 235.59 | 62.00 | 280.00 | 430.00 |
| failing | thompson_sampling | 2253 | 0 | 0.0000 | 249.83 | 60.00 | 240.00 | 420.00 |
| flapping | round_robin | 2515 | 0 | 0.0000 | 279.04 | 59.00 | 210.00 | 330.00 |
| flapping | least_connections | 2578 | 0 | 0.0000 | 285.93 | 59.00 | 210.00 | 350.00 |
| flapping | power_of_two_choices | 2532 | 0 | 0.0000 | 280.75 | 61.00 | 200.00 | 320.00 |
| flapping | ewma_latency | 1874 | 0 | 0.0000 | 207.70 | 66.00 | 330.00 | 520.00 |
| flapping | latency_aware | 2059 | 0 | 0.0000 | 228.33 | 66.00 | 280.00 | 400.00 |
| flapping | thompson_sampling | 2378 | 0 | 0.0000 | 263.82 | 60.00 | 240.00 | 380.00 |
