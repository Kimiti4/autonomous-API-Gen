from fastapi.testclient import TestClient

from app.main import app


def test_openapi_publishes_only_canonical_v1_api_paths():
    paths = app.openapi()["paths"]
    assert paths
    assert any(path.startswith("/api/v1/") for path in paths)
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
