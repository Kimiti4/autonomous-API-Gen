from fastapi.testclient import TestClient

from app.main import app


def test_openapi_publishes_only_canonical_v1_api_paths():
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/health": {"get"},
        "/api/v1/stream": {"get"},
        "/api/v1/production/readiness": {"post"},
        "/api/v1/evolve/start": {"post"},
        "/api/v1/evolve/runs": {"get"},
        "/api/v1/evolve/run/{run_id}": {"get"},
        "/api/v1/evolve/sync": {"post"},
        "/api/v1/evolve/elite/start": {"post"},
        "/api/v1/evolve/elite/insights": {"get"},
        "/api/v1/evolve/elite/clear-memory": {"post"},
        "/api/v1/evolve/elite/clear-memory/audit": {"get"},
        "/api/v1/observation/capabilities": {"get"},
        "/api/v1/observation/fitness": {"get"},
        "/api/v1/observation/isr": {"get"},
        "/api/v1/observation/snapshot": {"get"},
        "/api/v1/observation/state": {"get"},
        "/api/v1/governance/council": {"post"},
        "/api/v1/governance/gates": {"post"},
        "/api/v1/governance/policies": {"post"},
        "/api/v1/governance/gate-evaluations": {"post"},
        "/api/v1/governance/decisions": {"post"},
        "/api/v1/governance/certifications": {"post"},
        "/api/v1/governance/certifications/revoke": {"post"},
        "/api/v1/governance/candidate/{candidate_id}": {"get"},
        "/api/v1/governance/generation/{generation}": {"get"},
        "/api/v1/governance/audit/{candidate_id}": {"get"},
    }
    actual = {
        path: {method for method in operation if method in {"get", "post", "put", "patch", "delete"}}
        for path, operation in paths.items()
    }
    assert actual["/"] == {"get"}
    assert actual["/metrics"] == {"get"}
    assert {
        path: methods for path, methods in actual.items()
        if path not in {"/", "/metrics"}
    } == expected
    assert not any(
        path.startswith(("/evolve", "/observation", "/governance"))
        for path in paths
    )


def test_unversioned_alias_remains_compatible():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_versioned_control_surface_is_fail_closed():
    client = TestClient(app)
    response = client.post(
        "/api/v1/evolve/start",
        json={"generations": 1, "population_size": 2},
    )
    assert response.status_code == 401
