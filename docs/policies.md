# Routing policies

The proxy registry provides round-robin, least-connections, latency-aware, P2C with a bounded latency/load score, and smooth weighted round-robin. It also provides epsilon-greedy, UCB1, and Thompson-sampling selectors that choose among those five policies and learn from request outcomes. Policy inputs use proxy-measured in-flight counts, bounded health signals, and stable backend ordering. Policy decisions include a reason and candidate scores.

`BanditRouter` is the bounded exploration utility used by those selectors. Its rewards are a simple success/latency signal from the proxy, not an application-specific objective. The same applies to rendezvous hashing: it is a tested helper rather than a registered routing mode.

Latency-aware weights are validated from YAML and selected through the admin API. The selector is a deterministic heuristic, not a learned predictor. `make reproduce` compares the policies on the same generated synthetic scenarios; results do not establish production performance.

Computer vision is intentionally excluded: routing HTTP traffic has no image understanding input. Binary and large bodies are tested as transport correctness cases.
