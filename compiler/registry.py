"""
Compiler backend registry and target capability registry.
"""

from __future__ import annotations

from typing import Any

from .errors import BackendNotFoundError, BackendRegistrationError
from .models import BackendManifest, CapabilityQuery


class BackendRegistry:
    """Registry for compiler backends."""

    def __init__(self) -> None:
        self._backends: dict[str, Any] = {}
        self._manifests: dict[str, BackendManifest] = {}
        self._backend_ids: dict[str, list[str]] = {}

    def register_backend(self, backend: Any) -> None:
        """Register a compiler backend instance."""

        manifest = getattr(backend, "manifest", None)

        if not isinstance(manifest, BackendManifest):
            raise BackendRegistrationError(
                "Backend must expose a BackendManifest as 'manifest'."
            )

        self._register(manifest, backend)

    def register_manifest(
        self,
        manifest: BackendManifest,
        backend: Any = None,
    ) -> None:
        """Register a backend manifest directly.

        In Phase 25.1, this is used for certification-only registration
        where the actual backend may be loaded separately.
        """

        self._register(manifest, backend if backend is not None else {})

    def _register(self, manifest: BackendManifest, backend: Any) -> None:
        """Internal registration logic."""

        key = self._key(manifest.backend_id, manifest.version)

        if key in self._backends:
            raise BackendRegistrationError(
                f"Backend already registered: {key}"
            )

        self._backends[key] = backend
        self._manifests[key] = manifest

        self._backend_ids.setdefault(manifest.backend_id, []).append(key)

    def get_backend(
        self,
        backend_id: str,
        version: str | None = None,
    ) -> Any:
        """Get a backend by ID and optional version."""

        key = self._resolve_key(backend_id, version)
        return self._backends[key]

    def get_manifest(
        self,
        backend_id: str,
        version: str | None = None,
    ) -> BackendManifest:
        """Get a backend manifest."""

        key = self._resolve_key(backend_id, version)
        return self._manifests[key]

    def list_manifests(self) -> list[BackendManifest]:
        """List all registered backend manifests."""
        return list(self._manifests.values())

    def find_backends(self, query: CapabilityQuery) -> list[BackendManifest]:
        """Find backends matching capability requirements."""

        results: list[BackendManifest] = []

        for manifest in self._manifests.values():
            if self._matches(manifest, query):
                results.append(manifest)

        return results

    def _matches(
        self,
        manifest: BackendManifest,
        query: CapabilityQuery,
    ) -> bool:
        capabilities = manifest.capabilities

        checks: list[tuple[list[str], list[str]]] = [
            (query.supported_targets, capabilities.supported_targets),
            (query.languages, capabilities.languages),
            (query.frameworks, capabilities.frameworks),
            (query.artifact_types, capabilities.artifact_types),
            (query.deployment_targets, capabilities.deployment_targets),
        ]

        for requested, available in checks:
            if not requested:
                continue

            if not set(requested).issubset(set(available)):
                return False

        return True

    def _key(self, backend_id: str, version: str) -> str:
        return f"{backend_id}@{version}"

    def _resolve_key(
        self,
        backend_id: str,
        version: str | None,
    ) -> str:
        if version:
            key = self._key(backend_id, version)

            if key not in self._backends:
                raise BackendNotFoundError(
                    f"Backend not found: {key}"
                )

            return key

        candidates = self._backend_ids.get(backend_id, [])

        if not candidates:
            raise BackendNotFoundError(
                f"Backend not found: {backend_id}"
            )

        return sorted(candidates)[-1]