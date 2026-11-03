# Simulator and generated evidence

`routemesh.sim` is a deterministic discrete-event approximation for comparing routing behavior. It models a fixed arrival schedule, seeded service-time variation, backend failures, basic circuit transitions, and per-backend request shares. It is not a network or production load test.

`make bench-sim` runs the built-in policy/scenario matrix and writes `benchmarks/results/policy-comparison.json`. The same report is copied to `site/src/data/results.generated.json`, which the site renders. The report uses fixed seeds and includes confidence intervals over those synthetic runs.

`make reproduce` also exports policy decisions and a full seeded simulation result from Python into `site/src/features/simulator/__fixtures__/`. Vitest checks the TypeScript implementation against those fixtures. CI regenerates all outputs and fails if committed generated files are stale.

The offline tuner performs deterministic random search over latency-aware weights on a fixed overloaded synthetic scenario. Its selected weights and interval describe that search only; they are not a production tuning recommendation. The report also evaluates a fixed service graph for retry amplification, blast radius, and critical path.
