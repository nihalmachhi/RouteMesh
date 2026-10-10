"""Locust workload used for policy comparisons."""

import os

from locust import HttpUser, constant, task


class RouteMeshUser(HttpUser):
    """Issue repeatable GET requests to a configured RouteMesh path."""

    wait_time = constant(0)
    host = os.getenv("ROUTEMESH_TARGET_URL", "http://localhost:8000")

    @task
    def proxy_get(self) -> None:
        """Exercise a small stable route so policies see identical traffic."""
        self.client.get("/benchmark/ping", name="/benchmark/ping")
