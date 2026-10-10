# Decision 002: bounded request buffering

**Context:** The v1 proxy must forward methods, headers, query, and body while keeping resource use predictable.

**Decision:** Buffer request/response bodies through HTTPX but reject request bodies above ROUTEMESH_MAX_BODY_BYTES (10 MB by default). Do not claim large-body streaming support.

**Consequences:** This is simple and safe for a learning demo, but adds memory proportional to concurrent bounded requests. A production extension should add streaming with explicit backpressure and cancellation tests.
