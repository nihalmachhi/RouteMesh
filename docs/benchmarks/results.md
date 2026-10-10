# Benchmark results

No benchmark has been run in this environment, so there are no measured results to report.

Run `make bench` with Docker Compose already serving RouteMesh. The command uses the same headless Locust workload, user count, ramp-up, and duration for round-robin, least-connections, and latency-aware. It writes raw Locust CSV, a JSON summary, and a p95 chart under a timestamped directory in `output/benchmarks`.

Record the machine, Docker resource limits, backend behavior settings, active policy, sample duration, and commit SHA alongside any results you publish. Do not compare runs with different workload or failure conditions.
