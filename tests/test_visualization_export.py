"""
Tests for Phase 23.2 visualization and graph export runtime.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from knowledge.models import (
    Classification,
    EntityCreate,
    RelationCreate,
    SourceRef,
)
from knowledge.runtime import GraphRuntime
from knowledge.search import InMemorySearchStore
from knowledge.store import InMemoryGraphStore
from knowledge.visualization.routes import router as visualization_router


def build_app():
    graph_store = InMemoryGraphStore()
    search_store = InMemorySearchStore()
    runtime = GraphRuntime(
        graph_store=graph_store,
        search_store=search_store,
    )

    app = FastAPI()
    app.state.runtime = runtime
    app.include_router(visualization_router)

    return app, runtime


def seed_graph(runtime):
    source_ref = SourceRef(
        source_type="ISR_REVISION",
        source_id="isr_rev_100",
        source_hash="sha256:isr100",
    )

    service = runtime.create_entity(
        EntityCreate(
            entity_type="SERVICE",
            name="BillingService",
            namespace="billing",
            description="Handles billing.",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    api = runtime.create_entity(
        EntityCreate(
            entity_type="API",
            name="createInvoice",
            namespace="billing",
            description="Creates invoices.",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    secret_model = runtime.create_entity(
        EntityCreate(
            entity_type="DATA_MODEL",
            name="SecretLedger",
            namespace="billing",
            description="Restricted ledger model.",
            classification=Classification(sensitivity="RESTRICTED"),
            source_refs=[source_ref],
        ),
        actor="test",
    )

    runtime.create_relation(
        RelationCreate(
            relation_type="EXPOSES",
            source_entity_id=service.id,
            target_entity_id=api.id,
            source_refs=[source_ref],
        ),
        actor="test",
    )

    runtime.create_relation(
        RelationCreate(
            relation_type="USES",
            source_entity_id=service.id,
            target_entity_id=secret_model.id,
            source_refs=[source_ref],
        ),
        actor="test",
    )

    return service, api, secret_model


def test_export_json_excludes_sensitive_without_role():
    app, runtime = build_app()
    client = TestClient(app)

    service, api, secret_model = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/visualize/export",
        json={
            "root_entity_id": service.id,
            "depth": 2,
            "direction": "both",
            "format": "json",
        },
    )

    assert response.status_code == 200

    body = response.json()

    labels = {node["label"] for node in body["nodes"]}

    assert "BillingService" in labels
    assert "createInvoice" in labels
    assert "SecretLedger" not in labels

    assert body["metadata"]["unauthorized_nodes_removed"] >= 1


def test_export_json_includes_sensitive_for_auditor():
    app, runtime = build_app()
    client = TestClient(app)

    service, api, secret_model = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/visualize/export",
        json={
            "root_entity_id": service.id,
            "depth": 2,
            "direction": "both",
            "format": "json",
        },
        headers={
            "X-Actor-Id": "auditor",
            "X-Actor-Roles": "knowledge_auditor",
        },
    )

    assert response.status_code == 200

    body = response.json()
    labels = {node["label"] for node in body["nodes"]}

    assert "SecretLedger" in labels


def test_export_mermaid():
    app, runtime = build_app()
    client = TestClient(app)

    service, api, secret_model = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/visualize/export",
        json={
            "root_entity_id": service.id,
            "depth": 2,
            "direction": "both",
            "format": "mermaid",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["format"] == "mermaid"
    assert body["content"].startswith("graph TD")
    assert "BillingService" in body["content"]
    assert "createInvoice" in body["content"]


def test_export_dot():
    app, runtime = build_app()
    client = TestClient(app)

    service, api, secret_model = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/visualize/export",
        json={
            "root_entity_id": service.id,
            "depth": 2,
            "direction": "both",
            "format": "dot",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["format"] == "dot"
    assert body["content"].startswith("digraph KnowledgeGraph")
    assert "BillingService" in body["content"]


def test_export_missing_root_returns_404():
    app, runtime = build_app()
    client = TestClient(app)

    response = client.post(
        "/v1/knowledge/visualize/export",
        json={
            "root_entity_id": "entity_missing",
            "depth": 1,
        },
    )

    assert response.status_code == 404
