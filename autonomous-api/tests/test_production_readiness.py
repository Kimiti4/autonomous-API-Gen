from fastapi.testclient import TestClient

from app.engine.genome import Genome
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.main import app


def test_readiness_blocks_weak_critical_service_auth():
    analyzer = ProductionReadinessAnalyzer()
    genome = Genome(
        genome_data={
            "services": ["auth", "users", "payments"],
            "auth": "basic",
            "database": "sqlite",
            "cache_enabled": False,
            "rate_limiting": False,
            "cors_enabled": True,
            "logging_level": "DEBUG",
            "api_version": "v1",
        }
    )

    report = analyzer.analyze(genome, deployment_target="kubernetes")

    assert report["status"] == "blocked"
    assert report["score"] < 0.7
    assert report["blockers"]
    assert any("Critical services" in blocker for blocker in report["blockers"])
    assert any(risk["severity"] == "high" for risk in report["risk_register"])


def test_readiness_scores_strong_candidate_as_ready_or_reviewable():
    analyzer = ProductionReadinessAnalyzer()
    genome = Genome(
        genome_data={
            "services": ["auth", "users", "analytics"],
            "auth": "oauth2",
            "database": "postgres",
            "cache_enabled": True,
            "rate_limiting": True,
            "cors_enabled": True,
            "logging_level": "INFO",
            "api_version": "v2",
        }
    )

    report = analyzer.analyze(genome, deployment_target="kubernetes")

    assert report["status"] in {"ready", "needs_review"}
    assert report["score"] >= 0.7
    assert report["blockers"] == []
    assert "database_migrations" in report["required_capabilities"]
    assert "secret_management" in report["required_capabilities"]


def test_production_readiness_endpoint_returns_gate_report():
    client = TestClient(app)

    response = client.post(
        "/production/readiness",
        json={
            "deployment_target": "docker_compose",
            "genome": {
                "services": ["auth", "admin"],
                "auth": "api_key",
                "database": "sqlite",
                "cache_enabled": False,
                "rate_limiting": False,
                "cors_enabled": True,
                "logging_level": "ERROR",
                "api_version": "v1",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["deployment_target"] == "docker_compose"
    assert "dimensions" in data
    assert "risk_register" in data
