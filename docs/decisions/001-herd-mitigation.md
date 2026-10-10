# Decision 001: normalized in-flight penalty

**Context:** A minimum-latency policy can repeatedly select the current winner and create a herd before its latency estimate catches up.

**Decision:** Add a small configurable normalized in-flight term (default 0.1) to the latency, CPU, and error score. Keep deterministic backend ID tie-breaking. This avoids injecting randomness into pure strategies and keeps decisions reproducible.

**Consequences:** The penalty can shift traffic away from the lowest-latency backend under load. Compare p95, throughput, and distribution under the same benchmark conditions before adjusting weights.
