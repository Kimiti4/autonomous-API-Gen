"""
Tests for Phase 23.4 recommendation analytics runtime.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from knowledge.recommendations.routes import router as recommendation_analytics_router


def build_app():
    app = FastAPI()
    app.include_router(recommendation_analytics_router)
    return app


def test_high_priority_security_recommendation():
    app = build_app()
    client = TestClient(app)

    payload = {
        "recommendations": [
            {
                "id": "rec_security",
                "title": "Enforce mTLS",
                "description": "Enforce mutual TLS for service-to-service authentication.",
                "recommendation_type": "SECURITY",
                "suggested_action": "Enforce mTLS between internal services.",
                "target_entity_id": "entity_billing_service",
                "evidence_refs": ["signal_security_1"],
            },
            {
                "id": "rec_docs",
                "title": "Improve documentation",
                "description": "Improve operator documentation.",
                "recommendation_type": "DOCUMENTATION",
                "suggested_action": "Update runbooks.",
            },
        ],
        "signals": [
            {
                "signal_type": "SECURITY_FINDING",
                "source_id": "signal_security_1",
                "severity": "CRITICAL",
                "confidence": 0.95,
                "related_recommendation_ids": ["rec_security"],
            }
        ],
        "include_packet": True,
    }

    response = client.post(
        "/v1/knowledge/recommendations/analyze",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["analyzed_recommendations"] == 2
    assert body["ranked_recommendations"][0]["recommendation"]["id"] == "rec_security"
    assert body["ranked_recommendations"][0]["priority_level"] == "HIGH"
    assert body["packet"]["governance_status"] == "DRAFT"


def test_duplicate_detection():
    app = build_app()
    client = TestClient(app)

    payload = {
        "recommendations": [
            {
                "id": "rec_1",
                "title": "Enable retry policy",
                "description": "Enable retry policy for payment service calls.",
                "recommendation_type": "RELIABILITY",
                "suggested_action": "Enable retries.",
            },
            {
                "id": "rec_2",
                "title": "Enable retry policies",
                "description": "Enable retry policy for payment service communication.",
                "recommendation_type": "RELIABILITY",
                "suggested_action": "Enable retries.",
            },
        ],
        "duplicate_threshold": 0.55,
    }

    response = client.post(
        "/v1/knowledge/recommendations/duplicates",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["duplicate_cluster_count"] >= 1
    assert body["duplicate_clusters"][0]["recommendation_ids"] == ["rec_1", "rec_2"]


def test_conflict_detection():
    app = build_app()
    client = TestClient(app)

    payload = {
        "recommendations": [
            {
                "id": "rec_increase",
                "title": "Increase retry limit",
                "description": "Increase retry limit for billing calls.",
                "recommendation_type": "RELIABILITY",
                "suggested_action": "Increase retry limit.",
                "target_entity_id": "entity_billing_service",
            },
            {
                "id": "rec_decrease",
                "title": "Decrease retry limit",
                "description": "Decrease retry limit to reduce load.",
                "recommendation_type": "PERFORMANCE",
                "suggested_action": "Decrease retry limit.",
                "target_entity_id": "entity_billing_service",
            },
        ]
    }

    response = client.post(
        "/v1/knowledge/recommendations/conflicts",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["conflict_count"] >= 1
    assert body["conflicts"][0]["conflict_type"] == "OPPOSING_ACTION"


def test_sensitive_recommendation_is_excluded_without_role():
    app = build_app()
    client = TestClient(app)

    payload = {
        "recommendations": [
            {
                "id": "rec_restricted",
                "title": "Restricted security remediation",
                "description": "Restricted remediation plan.",
                "recommendation_type": "SECURITY",
                "suggested_action": "Rotate secrets.",
                "sensitivity": "RESTRICTED",
            }
        ]
    }

    response = client.post(
        "/v1/knowledge/recommendations/analyze",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["excluded_sensitive_count"] == 1
    assert body["metadata"]["analyzed_recommendations"] == 0


def test_sensitive_recommendation_visible_to_auditor():
    app = build_app()
    client = TestClient(app)

    payload = {
        "recommendations": [
            {
                "id": "rec_restricted",
                "title": "Restricted security remediation",
                "description": "Restricted remediation plan.",
                "recommendation_type": "SECURITY",
                "suggested_action": "Rotate secrets.",
                "sensitivity": "RESTRICTED",
            }
        ]
    }

    response = client.post(
        "/v1/knowledge/recommendations/analyze",
        json=payload,
        headers={
            "X-Actor-Id": "auditor",
            "X-Actor-Roles": "knowledge_auditor",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["metadata"]["excluded_sensitive_count"] == 0
    assert body["metadata"]["analyzed_recommendations"] == 1
