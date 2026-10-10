"""Typed exceptions shared by routing and proxy services."""


class RouteMeshError(Exception):
    """Base class for expected RouteMesh failures."""


class ConfigurationError(RouteMeshError):
    """Raised when the static service configuration is invalid."""


class NoHealthyBackend(RouteMeshError):
    """Raised when no eligible backend can serve a request."""


class CircuitOpen(RouteMeshError):
    """Raised when a backend circuit is not eligible for normal traffic."""


class ForwardingError(RouteMeshError):
    """Raised when forwarding fails before a response can be returned."""
