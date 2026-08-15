"""
Tests for the SQLite persistence adapters.
"""

from pathlib import Path

from knowledge.adapters.sqlite_stores import SQLiteGraphStore, SQLiteSearchStore
from knowledge.models import (
    EntityCreate,
    RelationCreate,
    SearchRequest,
    SourceRef,
)
from knowledge.runtime import GraphRuntime


def test_sqlite_graph_store_roundtrip(tmp_path: Path) -> None:
    db_path = str(tmp_path / "knowledge.db")

    graph_store = SQLiteGraphStore(db_path)
    search_store = SQLiteSearchStore(db_path)

    runtime = GraphRuntime(
        graph_store=graph_store,
        search_store=search_store,
    )

    source_ref = SourceRef(
        source_type="ISR_REVISION",
        source_id="isr_1",
        source_hash="sha256:abc",
    )

    service = runtime.create_entity(
        EntityCreate(
            entity_type="SERVICE",
            name="BillingService",
            namespace="billing",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    requirement = runtime.create_entity(
        EntityCreate(
            entity_type="REQUIREMENT",
            name="Billing requirement",
            namespace="requirement",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    runtime.create_relation(
        RelationCreate(
            relation_type="SATISFIES",
            source_entity_id=service.id,
            target_entity_id=requirement.id,
            source_refs=[source_ref],
        ),
        actor="test",
    )

    # Re-open the store to prove persistence.
    graph_store.close()
    search_store.close()

    reopened_graph_store = SQLiteGraphStore(db_path)
    reopened_search_store = SQLiteSearchStore(db_path)

    reopened_runtime = GraphRuntime(
        graph_store=reopened_graph_store,
        search_store=reopened_search_store,
    )

    fetched_service = reopened_runtime.get_entity(service.id)
    assert fetched_service.name == "BillingService"

    trace = reopened_runtime.query(
        {
            "query_type": "TRACE",
            "entity_id": service.id,
            "direction": "both",
            "depth": 2,
        }
    )

    node_names = {node["name"] for node in trace["nodes"]}

    assert "BillingService" in node_names
    assert "Billing requirement" in node_names

    reopened_graph_store.close()
    reopened_search_store.close()


def test_sqlite_search_persists(tmp_path: Path) -> None:
    db_path = str(tmp_path / "knowledge.db")

    graph_store = SQLiteGraphStore(db_path)
    search_store = SQLiteSearchStore(db_path)

    runtime = GraphRuntime(
        graph_store=graph_store,
        search_store=search_store,
    )

    source_ref = SourceRef(
        source_type="ISR_REVISION",
        source_id="isr_1",
        source_hash="sha256:abc",
    )

    runtime.create_entity(
        EntityCreate(
            entity_type="SERVICE",
            name="BillingService",
            namespace="billing",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    search_store.close()
    graph_store.close()

    reopened_graph_store = SQLiteGraphStore(db_path)
    reopened_search_store = SQLiteSearchStore(db_path)
    reopened_runtime = GraphRuntime(
        graph_store=reopened_graph_store,
        search_store=reopened_search_store,
    )

    response = reopened_runtime.search(
        SearchRequest(text="billing", entity_types=["SERVICE"], limit=10)
    )

    names = {result.name for result in response.results}

    assert "BillingService" in names

    reopened_search_store.close()
    reopened_graph_store.close()
