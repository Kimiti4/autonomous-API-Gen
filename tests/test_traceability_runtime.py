"""
Tests for Phase 23.3 advanced traceability and impact explanation runtime.
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
from knowledge.traceability.routes import router as traceability_router


def build_app():
    graph_store = InMemoryGraphStore()
    search_store = InMemorySearchStore()

    runtime = GraphRuntime(
        graph_store=graph_store,
        search_store=search_store,
    )

    app = FastAPI()
    app.state.runtime = runtime
    app.include_router(traceability_router)

    return app, runtime


def seed_graph(runtime):
    source_ref = SourceRef(
        source_type="ISR_REVISION",
        source_id="isr_rev_100",
        source_hash="sha256:isr100",
    )

    isr = runtime.create_entity(
        EntityCreate(
            entity_type="ISR_REVISION",
            name="BillingISR",
            namespace="isr",
            source_refs=[source_ref],
        ),
        actor="test",
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

    api = runtime.create_entity(
        EntityCreate(
            entity_type="API",
            name="createInvoice",
            namespace="billing",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    dependency = runtime.create_entity(
        EntityCreate(
            entity_type="SERVICE",
            name="PaymentService",
            namespace="payments",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    requirement = runtime.create_entity(
        EntityCreate(
            entity_type="REQUIREMENT",
            name="BillingRequirement",
            namespace="requirements",
            source_refs=[source_ref],
        ),
        actor="test",
    )

    secret = runtime.create_entity(
        EntityCreate(
            entity_type="DATA_MODEL",
            name="SecretLedger",
            namespace="billing",
            classification=Classification(sensitivity="RESTRICTED"),
            source_refs=[source_ref],
        ),
        actor="test",
    )

    runtime.create_relation(
        RelationCreate(
            relation_type="DERIVES_FROM",
            source_entity_id=service.id,
            target_entity_id=isr.id,
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
            relation_type="DEPENDS_ON",
            source_entity_id=service.id,
            target_entity_id=dependency.id,
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

    runtime.create_relation(
        RelationCreate(
            relation_type="USES",
            source_entity_id=service.id,
            target_entity_id=secret.id,
            source_refs=[source_ref],
        ),
        actor="test",
    )

    return {
        "isr": isr,
        "service": service,
        "api": api,
        "dependency": dependency,
        "requirement": requirement,
        "secret": secret,
    }


def test_forward_impact_from_dependency():
    app, runtime = build_app()
    client = TestClient(app)

    entities = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/trace/impact",
        json={
            "entity_id": entities["dependency"].id,
            "mode": "forward",
            "depth": 3,
        },
    )

    assert response.status_code == 200

    body = response.json()
    names = {entry["name"] for entry in body["entries"]}

    assert "BillingService" in names
    assert "createInvoice" in names

    service_entry = next(
        entry
        for entry in body["entries"]
        if entry["name"] == "BillingService"
    )

    api_entry = next(
        entry
        for entry in body["entries"]
        if entry["name"] == "createInvoice"
    )

    assert service_entry["direct"] is True
    assert service_entry["transitive"] is False

    assert api_entry["direct"] is False
    assert api_entry["transitive"] is True

    assert service_entry["score"] > api_entry["score"]


def test_backward_impact_from_service():
    app, runtime = build_app()
    client = TestClient(app)

    entities = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/trace/impact",
        json={
            "entity_id": entities["service"].id,
            "mode": "backward",
            "depth": 3,
        },
    )

    assert response.status_code == 200

    body = response.json()
    names = {entry["name"] for entry in body["entries"]}

    assert "BillingISR" in names
    assert "BillingRequirement" in names
    assert "PaymentService" in names


def test_path_explanation_from_isr_to_api():
    app, runtime = build_app()
    client = TestClient(app)

    entities = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/trace/explain",
        json={
            "source_entity_id": entities["isr"].id,
            "target_entity_id": entities["api"].id,
            "depth": 4,
            "max_paths": 3,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["path_count"] >= 1

    path = body["paths"][0]

    assert path["entity_ids"][0] == entities["isr"].id
    assert path["entity_ids"][-1] == entities["api"].id

    assert "DERIVES_FROM" in path["human_summary"]
    assert "EXPOSES" in path["human_summary"]

    assert path["confidence"] > 0.0


def test_sensitive_root_is_hidden_without_role():
    app, runtime = build_app()
    client = TestClient(app)

    entities = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/trace/impact",
        json={
            "entity_id": entities["secret"].id,
            "mode": "forward",
            "depth": 2,
        },
    )

    assert response.status_code == 404


def test_sensitive_root_is_visible_to_auditor():
    app, runtime = build_app()
    client = TestClient(app)

    entities = seed_graph(runtime)

    response = client.post(
        "/v1/knowledge/trace/impact",
        json={
            "entity_id": entities["secret"].id,
            "mode": "forward",
            "depth": 2,
        },
        headers={
            "X-Actor-Id": "auditor",
            "X-Actor-Roles": "knowledge_auditor",
        },
    )

    assert response.status_code == 200

    body = response.json()
    names = {entry["name"] for entry in body["entries"]}

    assert "BillingService" in names
