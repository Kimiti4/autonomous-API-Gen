"""Governance observation projection is authenticated, read-only, and canonical-backed."""
from __future__ import annotations

from app.api import observation_routes


class _FakeGovernanceProjector:
    async def get_candidate(self, candidate_id):
        return {"candidateId": candidate_id, "governance": {"currentState": "certified"}}

    async def get_generation(self, generation):
        return {"generation": generation, "candidates": []}


def test_governance_observation_candidate_requires_auth(client):
    observation_routes._governance_projector = _FakeGovernanceProjector()
    response = client.get("/api/v1/observation/governance/candidate/c1")
    assert response.status_code == 401


def test_governance_observation_candidate_is_served(client, auth_headers):
    observation_routes._governance_projector = _FakeGovernanceProjector()
    response = client.get(
        "/api/v1/observation/governance/candidate/c1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "candidateId": "c1",
        "governance": {"currentState": "certified"},
    }


def test_governance_observation_generation_is_served(client, auth_headers):
    observation_routes._governance_projector = _FakeGovernanceProjector()
    response = client.get(
        "/api/v1/observation/governance/generation/7",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"generation": 7, "candidates": []}


def test_governance_observation_unconfigured_fails_closed(client, auth_headers):
    observation_routes._governance_projector = None
    response = client.get(
        "/api/v1/observation/governance/candidate/c1",
        headers=auth_headers,
    )
    assert response.status_code == 503
