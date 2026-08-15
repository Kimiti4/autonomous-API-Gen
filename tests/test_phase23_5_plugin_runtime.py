"""
Tests for Phase 23.5 external graph and search plugin runtime.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from knowledge.plugins.bootstrap import (
    bootstrap_default_plugins,
    create_default_registry,
)
from knowledge.plugins.testing import (
    run_graph_store_contract_tests,
    run_search_store_contract_tests,
)


def test_registry_creates_sqlite_graph_plugin(tmp_path):
    registry = create_default_registry()

    database_path = str(tmp_path / "graph.db")

    graph_store = registry.create_graph_store(
        "sqlite.graph",
        {
            "database_path": database_path,
        },
    )

    health = graph_store.health_check()

    assert health.plugin_id == "sqlite.graph"
    assert health.status == "ok"

    graph_store.close()


def test_registry_creates_sqlite_search_plugin(tmp_path):
    registry = create_default_registry()

    database_path = str(tmp_path / "search.db")

    search_store = registry.create_search_store(
        "sqlite.search",
        {
            "database_path": database_path,
        },
    )

    health = search_store.health_check()

    assert health.plugin_id == "sqlite.search"
    assert health.status == "ok"

    search_store.close()


def test_sqlite_graph_plugin_passes_contract_tests(tmp_path):
    registry = create_default_registry()

    database_path = str(tmp_path / "graph_contract.db")

    graph_store = registry.create_graph_store(
        "sqlite.graph",
        {
            "database_path": database_path,
        },
    )

    run_graph_store_contract_tests(graph_store)

    graph_store.close()


def test_sqlite_search_plugin_passes_contract_tests(tmp_path):
    registry = create_default_registry()

    database_path = str(tmp_path / "search_contract.db")

    search_store = registry.create_search_store(
        "sqlite.search",
        {
            "database_path": database_path,
        },
    )

    run_search_store_contract_tests(search_store)

    search_store.close()


def test_plugin_routes(tmp_path):
    app = FastAPI()

    database_path = str(tmp_path / "app.db")

    bootstrap_default_plugins(app, database_path)

    client = TestClient(app)

    plugins_response = client.get("/v1/knowledge/plugins")

    assert plugins_response.status_code == 200

    plugins = plugins_response.json()

    plugin_ids = {plugin["plugin_id"] for plugin in plugins}

    assert "sqlite.graph" in plugin_ids
    assert "sqlite.search" in plugin_ids

    health_response = client.get("/v1/knowledge/plugins/health")

    assert health_response.status_code == 200

    health = health_response.json()

    health_by_plugin = {item["plugin_id"]: item["status"] for item in health}

    assert health_by_plugin["sqlite.graph"] == "ok"
    assert health_by_plugin["sqlite.search"] == "ok"