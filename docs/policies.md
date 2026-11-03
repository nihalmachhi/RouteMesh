# Routing policies

The proxy currently offers round-robin, least-connections, and latency-aware
selection. The first two use measured proxy in-flight counts and stable backend
ordering. Latency-aware selection scores the latest registry snapshot using
configured latency, CPU, error, and in-flight weights; it is a heuristic, not a
learned predictor.

Computer vision is intentionally excluded. RouteMesh routes HTTP requests and
has no image understanding problem. Binary request and response bodies are
transport data; forwarding them byte-for-byte is a correctness requirement.
