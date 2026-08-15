"""
Registration helpers for production compiler backends.
"""

from __future__ import annotations

from ...registry import BackendRegistry
from .cicd_backend import GitHubActionsBackend
from .docker_backend import DockerDeploymentBackend
from .fastapi_backend import FastAPIFoundationBackend
from .openapi_backend import OpenAPIBackend
from .postgres_backend import PostgresSchemaBackend


def register_production_backends(registry: BackendRegistry) -> None:
    """Register the first production compiler backends."""

    registry.register_backend(OpenAPIBackend())
    registry.register_backend(PostgresSchemaBackend())
    registry.register_backend(FastAPIFoundationBackend())
    registry.register_backend(DockerDeploymentBackend())
    registry.register_backend(GitHubActionsBackend())