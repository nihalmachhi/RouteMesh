# Threat model and operating boundary

RouteMesh is a lab and learning reverse proxy. The proxy forwards only to
backends loaded from the validated local configuration; clients cannot choose
an upstream URL. Do not expose the demo backend control API or operations API
to an untrusted network. Admin endpoints fail closed when no token is
configured. Configure a strong secret and restrict network access to the
operations port.

The current process uses an in-memory backend registry and telemetry. It is not
a multi-tenant or production service mesh, and it does not provide TLS
termination, dynamic service discovery, or distributed control-plane
consistency. Treat all benchmark and simulator outputs as development evidence.
