# Security policy

RouteMesh is a lab and learning reverse proxy. Do not expose the demo stack to
untrusted networks. The proxy only routes to endpoints from its validated
configuration; never add request-controlled upstream URLs.

To report a security issue, use GitHub's private vulnerability reporting for
this repository. Please include affected commit/version, configuration, and a
reproduction that does not expose credentials or real user data. Do not open a
public issue for an unpatched vulnerability.

Only the current `main` branch is supported. This project does not promise
production service-mesh security or availability guarantees.
