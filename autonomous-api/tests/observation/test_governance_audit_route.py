"""Governance audit trail route: authenticated, chain-verified, observable."""
from __future__ import annotations

import asyncio

from sqlalchemy import create_engine

from app.api.governance_routes import candidate_audit
from app.core.contracts.governance import GovernanceDecision
from app.core.governance.events import GovernanceDecisionMade
from app.governance.adapters import sqlite as sqlite_adapter
from app.governance.adapters.sqlite import (
    SqliteGovernanceEventStore,
    SqliteGovernanceReferenceStore,
)
from app.governance.subsystem import GovernanceSubsystem
from app.storage.migrations import migrate


def _compose_signed_candidate(monkeypatch, candidate_id: str) -> None:
    engine = create_engine("sqlite:///:memory:")
    migrate(engine)
    monkeypatch.setattr(sqlite_adapter, "engine", engine)
    store = SqliteGovernanceEventStore("route-test-key")
    subsystem = GovernanceSubsystem(
        event_store=store,
        reference_store=SqliteGovernanceReferenceStore(),
        recognized_certifiers={"certifier-1"},
    )
    monkeypatch.setattr("app.governance.runtime._governance", subsystem)
    decision = GovernanceDecision(
        decisionId="d-route",
        candidateId=candidate_id,
        generation=0,
        verdict="approve",
        fromState="proposed",
        toState="evaluating",
        authorizesTransition=True,
        decidedBy=["executive"],
        rationale="r",
        evidenceRefs=[],
        decidedAt="2026-09-26T00:00:00+00:00",
    )
    asyncio.run(store.append(candidate_id, [GovernanceDecisionMade(decision=decision)]))


def test_audit_route_serves_verified_chain(monkeypatch):
    _compose_signed_candidate(monkeypatch, "c1")

    response = asyncio.run(candidate_audit("c1"))

    assert response["candidateId"] == "c1"
    assert response["verified"] is True
    assert len(response["records"]) == 1
    record = response["records"][0]
    assert record["candidateId"] == "c1"
    assert record["sequence"] == 1
    assert record["previousHash"] == ""
    assert record["eventType"] == "GovernanceDecisionMade"
    assert record["recordHash"]
    assert record["signature"]


def test_audit_route_requires_authentication(client):
    response = client.get("/governance/audit/c1")
    assert response.status_code == 401


def test_audit_route_authenticated_empty_chain(client, auth_headers):
    response = client.get(
        "/governance/audit/no-such-candidate", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidateId"] == "no-such-candidate"
    assert body["verified"] is True
    assert body["records"] == []
