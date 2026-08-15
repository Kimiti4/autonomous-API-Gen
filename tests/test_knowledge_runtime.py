"""
Phase 23 Knowledge Graph runtime tests.
"""

from fastapi.testclient import TestClient

from knowledge.api import app


client = TestClient(app)


def test_health_live() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_health_ready() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_entity_requires_provenance() -> None:
    response = client.post(
        "/v1/knowledge/entities",
        json={
            "entity_type": "SERVICE",
            "name": "BillingService",
            "namespace": "billing",
            "source_refs": [],
        },
    )

    assert response.status_code == 422


def test_unknown_entity_type_is_rejected() -> None:
    response = client.post(
        "/v1/knowledge/entities",
        json={
            "entity_type": "NOT_A_VALID_TYPE",
            "name": "BadEntity",
            "namespace": "test",
            "source_refs": [
                {
                    "source_type": "ISR_REVISION",
                    "source_id": "isr_1",
                    "source_hash": "sha256:abc",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "Unknown entity type" in response.json()["message"]


def test_ingest_isr_and_trace() -> None:
    payload = {
        "source_type": "ISR_REVISION",
        "source_id": "isr_rev_100",
        "source_hash": "sha256:isr100",
        "payload": {
            "name": "BillingISR",
            "requirements": [
                {
                    "name": "Billing requirement",
                    "satisfied_by": ["BillingService"],
                }
            ],
            "domains": [
                {
                    "name": "billing",
                    "services": [
                        {
                            "name": "BillingService",
                            "apis": ["createInvoice"],
                            "produces_events": ["InvoiceCreated"],
                            "consumes_events": [],
                            "data_models": ["Invoice"],
                            "depends_on": [],
                        }
                    ],
                }
            ],
        },
    }

    response = client.post("/v1/knowledge/ingest", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUCCEEDED"
    assert len(body["produced_entities"]) > 0
    assert len(body["produced_relations"]) > 0

    entities_response = client.get("/v1/knowledge/entities")
    assert entities_response.status_code == 200

    entities = entities_response.json()

    service = next(
        entity
        for entity in entities
        if entity["name"] == "BillingService"
    )

    trace_response = client.get(
        f"/v1/knowledge/trace/{service['id']}/backward?depth=3"
    )

    assert trace_response.status_code == 200

    trace = trace_response.json()
    node_names = {node["name"] for node in trace["nodes"]}

    assert "BillingService" in node_names
    assert "Billing requirement" in node_names
    assert "BillingISR" in node_names


def test_search() -> None:
    response = client.post(
        "/v1/knowledge/search",
        json={
            "text": "billing",
            "entity_types": ["SERVICE"],
            "limit": 10,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert "results" in body

    names = {result["name"] for result in body["results"]}
    assert "BillingService" in names
