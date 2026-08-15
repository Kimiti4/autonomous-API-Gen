"""
Tests for Phase 24 Autonomous Product Factory.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from product_factory.api import enable_product_factory


def build_client() -> TestClient:
    app = FastAPI()
    enable_product_factory(app)
    return TestClient(app)


def test_build_product_pipeline():
    client = build_client()

    response = client.post(
        "/v1/product-factory/build",
        json={
            "name": "Invoice Automation Cloud",
            "problem_statement": "Manual invoice reconciliation is slow and error-prone.",
            "target_market": "Finance operations teams",
            "business_model_hypothesis": "subscription",
            "assumptions": {
                "visitors": 20000,
                "signup_conversion": 0.06,
                "activation_rate": 0.45,
                "paid_conversion": 0.12,
                "monthly_churn": 0.04,
                "months": 12,
            },
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["product_id"]
    assert body["status"] == "BUILT"

    assert body["opportunity"]["name"] == "Invoice Automation Cloud"
    assert body["research"]["segments"]
    assert body["strategy"]["core_capabilities"]
    assert body["brand"]["tagline"]
    assert body["ux"]["flows"]
    assert body["pricing"]["tiers"]
    assert body["revenue"]["scenarios"]
    assert body["marketing"]["channels"]
    assert body["deployment"]["approval_required"] is True

    assert body["isr"]["isr_id"]
    assert body["isr"]["security"]["authentication"] == "OIDC"
    assert body["isr"]["observability"]["metrics"] is True
    assert body["isr"]["testing"]["security_tests"] is True


def test_product_launch_requires_approval():
    client = build_client()

    build_response = client.post(
        "/v1/product-factory/build",
        json={
            "name": "Support Analytics",
            "problem_statement": "Support teams lack actionable analytics.",
            "target_market": "Customer support leaders",
            "business_model_hypothesis": "subscription",
        },
    )

    product_id = build_response.json()["product_id"]

    denied_response = client.post(
        f"/v1/product-factory/{product_id}/launch",
        json={
            "approval_refs": [],
        },
    )

    assert denied_response.status_code == 200
    assert denied_response.json()["allowed"] is False

    approved_response = client.post(
        f"/v1/product-factory/{product_id}/launch",
        json={
            "approval_refs": ["governance_approval_1"],
        },
    )

    assert approved_response.status_code == 200
    assert approved_response.json()["allowed"] is True


def test_analytics_events_and_report():
    client = build_client()

    build_response = client.post(
        "/v1/product-factory/build",
        json={
            "name": "Customer Health Monitor",
            "problem_statement": "CS teams miss churn signals.",
            "target_market": "Customer success teams",
            "business_model_hypothesis": "subscription",
        },
    )

    product_id = build_response.json()["product_id"]

    events_response = client.post(
        f"/v1/product-factory/{product_id}/analytics/events",
        json={
            "events": [
                {
                    "event_type": "signup",
                    "user_id": "user_1",
                },
                {
                    "event_type": "activated",
                    "user_id": "user_1",
                },
                {
                    "event_type": "payment_succeeded",
                    "user_id": "user_1",
                    "value": 99.0,
                },
                {
                    "event_type": "signup",
                    "user_id": "user_2",
                },
                {
                    "event_type": "churned",
                    "user_id": "user_2",
                },
            ],
        },
    )

    assert events_response.status_code == 201
    assert events_response.json()["ingested_events"] == 5

    report_response = client.get(
        f"/v1/product-factory/{product_id}/analytics/report"
    )

    assert report_response.status_code == 200

    report = report_response.json()

    assert report["total_signups"] == 2
    assert report["total_activations"] == 1
    assert report["total_payments"] == 1
    assert report["mrr"] == 99.0
    assert report["activation_rate"] == 0.5
    assert report["churn_rate"] == 1.0
    assert report["recommendations"]


def test_revenue_simulation_and_isr_retrieval():
    client = build_client()

    build_response = client.post(
        "/v1/product-factory/build",
        json={
            "name": "Onboarding Optimizer",
            "problem_statement": "New users drop off without value.",
            "target_market": "SaaS growth teams",
            "business_model_hypothesis": "subscription",
        },
    )

    product_id = build_response.json()["product_id"]

    simulation_response = client.post(
        f"/v1/product-factory/{product_id}/revenue/simulate",
        json={
            "visitors": 25000,
            "signup_conversion": 0.07,
            "activation_rate": 0.5,
            "paid_conversion": 0.15,
            "monthly_churn": 0.03,
            "months": 12,
        },
    )

    assert simulation_response.status_code == 200
    sim = simulation_response.json()
    assert sim["product_id"] == product_id
    assert len(sim["scenarios"]) == 3

    isr_response = client.get(
        f"/v1/product-factory/{product_id}/isr"
    )

    assert isr_response.status_code == 200
    isr = isr_response.json()
    assert isr["isr_id"]
    assert "domains" in isr
    assert isr["security"]["authentication"] == "OIDC"


def test_get_nonexistent_product_report_returns_404():
    client = build_client()

    response = client.get(
        "/v1/product-factory/nonexistent_product/report"
    )

    assert response.status_code == 404


def test_discover_opportunities():
    client = build_client()

    response = client.post(
        "/v1/product-factory/opportunities/discover",
        json={
            "ideas": [
                {
                    "name": "Invoice Automation Cloud",
                    "problem_statement": "Manual invoice reconciliation is slow and error-prone.",
                    "target_market": "Finance operations teams",
                    "business_model": "subscription",
                    "severity_score": 0.8,
                    "market_size_score": 0.7,
                    "feasibility_score": 0.75,
                    "strategic_alignment_score": 0.8,
                }
            ]
        },
    )

    assert response.status_code == 200
    opportunities = response.json()
    assert len(opportunities) == 1
    assert opportunities[0]["name"] == "Invoice Automation Cloud"
    assert opportunities[0]["total_score"] > 0
    assert opportunities[0]["status"] == "DISCOVERED"


def test_build_product_includes_billing_service_for_billing_keywords():
    client = build_client()

    response = client.post(
        "/v1/product-factory/build",
        json={
            "name": "Billing Automation",
            "problem_statement": "Billing is slow and error-prone.",
            "target_market": "Finance teams",
            "business_model_hypothesis": "subscription",
        },
    )

    assert response.status_code == 201
    isr = response.json()["isr"]

    service_names = [s["name"] for s in isr["domains"][0]["services"]]
    assert "BillingService" in service_names
