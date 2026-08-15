"""
Plugin registry.

The registry stores plugin manifests and factories.

It does not load arbitrary code dynamically in this phase. Dynamic plugin
loading, signing, and marketplace distribution should be added under
governance in later phases.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .manifest import PluginCapability, PluginManifest


class PluginRegistrationError(Exception):
    """Raised when plugin registration fails."""


class PluginNotFoundError(Exception):
    """Raised when a requested plugin is not registered."""


class PluginCapabilityError(Exception):
    """Raised when a plugin does not provide a required capability."""


PluginFactory = Callable[[dict[str, Any]], Any]


class PluginRegistry:
    """Registry for Knowledge Graph plugins."""

    def __init__(self) -> None:
        self._manifests: dict[str, PluginManifest] = {}
        self._factories: dict[str, PluginFactory] = {}

    def register(
        self,
        manifest: PluginManifest,
        factory: PluginFactory,
    ) -> None:
        """Register a plugin manifest and factory."""

        if not manifest.capabilities:
            raise PluginRegistrationError(
                f"Plugin {manifest.plugin_id} declares no capabilities."
            )

        key = self._key(manifest.plugin_id, manifest.version)

        if key in self._manifests:
            raise PluginRegistrationError(
                f"Plugin already registered: {key}"
            )

        self._manifests[key] = manifest
        self._factories[key] = factory

    def list_manifests(self) -> list[PluginManifest]:
        """List registered plugin manifests."""
        return list(self._manifests.values())

    def get_manifest(
        self,
        plugin_id: str,
        version: Optional[str] = None,
    ) -> PluginManifest:
        """Get a registered plugin manifest."""

        key = self._resolve_key(plugin_id, version)
        return self._manifests[key]

    def create(
        self,
        plugin_id: str,
        config: dict[str, Any],
        version: Optional[str] = None,
    ) -> Any:
        """Create a plugin instance."""

        key = self._resolve_key(plugin_id, version)
        factory = self._factories[key]

        return factory(config or {})

    def create_graph_store(
        self,
        plugin_id: str,
        config: dict[str, Any],
        version: Optional[str] = None,
    ) -> Any:
        """Create a graph store plugin instance."""

        manifest = self.get_manifest(plugin_id, version)

        if PluginCapability.GRAPH_STORE not in manifest.capabilities:
            raise PluginCapabilityError(
                f"Plugin {plugin_id} does not provide graph_store capability."
            )

        return self.create(plugin_id, config, version)

    def create_search_store(
        self,
        plugin_id: str,
        config: dict[str, Any],
        version: Optional[str] = None,
    ) -> Any:
        """Create a search store plugin instance."""

        manifest = self.get_manifest(plugin_id, version)

        if PluginCapability.SEARCH_STORE not in manifest.capabilities:
            raise PluginCapabilityError(
                f"Plugin {plugin_id} does not provide search_store capability."
            )

        return self.create(plugin_id, config, version)

    def _key(self, plugin_id: str, version: str) -> str:
        return f"{plugin_id}@{version}"

    def _resolve_key(
        self,
        plugin_id: str,
        version: Optional[str],
    ) -> str:
        if version:
            key = self._key(plugin_id, version)

            if key not in self._manifests:
                raise PluginNotFoundError(
                    f"Plugin not found: {key}"
                )

            return key

        candidates = [
            key
            for key in self._manifests
            if key.startswith(f"{plugin_id}@")
        ]

        if not candidates:
            raise PluginNotFoundError(
                f"Plugin not found: {plugin_id}"
            )

        return sorted(candidates)[-1]