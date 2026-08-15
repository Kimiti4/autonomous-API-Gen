"""
SQLite reference plugin.

This plugin wraps the Phase 23.1 SQLite stores and exposes them through
the Phase 23.5 plugin runtime.
"""

from __future__ import annotations

from typing import Any

from ..models import utcnow
from ..plugins.manifest import PluginCapability, PluginHealth, PluginManifest
from .sqlite_stores import SQLiteGraphStore, SQLiteSearchStore


SQLITE_GRAPH_MANIFEST = PluginManifest(
    plugin_id="sqlite.graph",
    name="SQLite Graph Store",
    version="0.1.0",
    description=(
        "SQLite-backed graph store reference plugin. "
        "Suitable for local development, tests, and small deployments."
    ),
    capabilities=[PluginCapability.GRAPH_STORE],
    entrypoint="knowledge.adapters.sqlite_plugin:sqlite_graph_factory",
    config_schema={
        "type": "object",
        "properties": {
            "database_path": {
                "type": "string",
                "description": "Path to the SQLite database file.",
            }
        },
        "required": [
            "database_path",
        ],
    },
    requires_external_dependencies=False,
)


SQLITE_SEARCH_MANIFEST = PluginManifest(
    plugin_id="sqlite.search",
    name="SQLite Search Store",
    version="0.1.0",
    description=(
        "SQLite-backed lexical search store reference plugin. "
        "Suitable for local development, tests, and small deployments."
    ),
    capabilities=[PluginCapability.SEARCH_STORE],
    entrypoint="knowledge.adapters.sqlite_plugin:sqlite_search_factory",
    config_schema={
        "type": "object",
        "properties": {
            "database_path": {
                "type": "string",
                "description": "Path to the SQLite database file.",
            }
        },
        "required": [
            "database_path",
        ],
    },
    requires_external_dependencies=False,
)


class SQLiteGraphStorePlugin(SQLiteGraphStore):
    """SQLite graph store plugin with health checking."""

    def __init__(self, config: dict[str, Any]) -> None:
        database_path = str(config.get("database_path", "")).strip()

        if not database_path:
            raise ValueError("database_path is required")

        super().__init__(database_path)

        self.manifest = SQLITE_GRAPH_MANIFEST
        self._ensure_migration_table()

    def health_check(self) -> PluginHealth:
        try:
            with self._lock:
                self._conn.execute("SELECT 1")

            return PluginHealth(
                plugin_id=self.manifest.plugin_id,
                status="ok",
                message="SQLite graph store is healthy.",
                details={
                    "database_path": self._database_path,
                },
            )
        except Exception as exc:
            return PluginHealth(
                plugin_id=self.manifest.plugin_id,
                status="error",
                message=str(exc),
            )

    def _ensure_migration_table(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                INSERT OR IGNORE INTO knowledge_schema_migrations (
                    version,
                    applied_at
                )
                VALUES (?, ?)
                """,
                (
                    "0.1.0",
                    utcnow().isoformat(),
                ),
            )

            self._conn.commit()


class SQLiteSearchStorePlugin(SQLiteSearchStore):
    """SQLite search store plugin with health checking."""

    def __init__(self, config: dict[str, Any]) -> None:
        database_path = str(config.get("database_path", "")).strip()

        if not database_path:
            raise ValueError("database_path is required")

        super().__init__(database_path)

        self.manifest = SQLITE_SEARCH_MANIFEST
        self._ensure_migration_table()

    def health_check(self) -> PluginHealth:
        try:
            with self._lock:
                self._conn.execute("SELECT 1")

            return PluginHealth(
                plugin_id=self.manifest.plugin_id,
                status="ok",
                message="SQLite search store is healthy.",
                details={
                    "database_path": self._database_path,
                },
            )
        except Exception as exc:
            return PluginHealth(
                plugin_id=self.manifest.plugin_id,
                status="error",
                message=str(exc),
            )

    def _ensure_migration_table(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                INSERT OR IGNORE INTO knowledge_schema_migrations (
                    version,
                    applied_at
                )
                VALUES (?, ?)
                """,
                (
                    "0.1.0",
                    utcnow().isoformat(),
                ),
            )

            self._conn.commit()


def sqlite_graph_factory(config: dict[str, Any]) -> SQLiteGraphStorePlugin:
    """Factory for the SQLite graph store plugin."""
    return SQLiteGraphStorePlugin(config)


def sqlite_search_factory(config: dict[str, Any]) -> SQLiteSearchStorePlugin:
    """Factory for the SQLite search store plugin."""
    return SQLiteSearchStorePlugin(config)