"""Durable governance adapter acceptance tests.

These tests use a temporary SQLite database by replacing the adapter's
module-level engine, proving persistence survives adapter reconstruction.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import create_engine, text

from app.core.contracts.governance import CouncilComposition, CouncilMember, GovernanceGate, PolicySummary, TransitionRef
from app.core.governance.events import GovernanceDecisionMade
from app.governance.adapters import sqlite as governance_sqlite


def test_sqlite_governance_reference_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'governance.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE governance_council (registry_key VARCHAR PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE governance_gates (gate_id VARCHAR PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE governance_policies (policy_id VARCHAR PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE governance_events (id INTEGER PRIMARY KEY, candidate_id VARCHAR NOT NULL, event_type VARCHAR NOT NULL, payload TEXT NOT NULL)"
        )

    original = governance_sqlite.engine
    governance_sqlite.engine = engine
    try:
        refs = governance_sqlite.SqliteGovernanceReferenceStore()
        council = CouncilComposition(
            members=[
                CouncilMember(
                    memberId="m1", name="Alice", role="chair", votingWeight=0.6
                )
            ]
        )
        gate = GovernanceGate(
            gateId="g1",
            name="intake",
            category="intake",
            guards=[TransitionRef(fromState="proposed", toState="evaluating")],
        )
        policy = PolicySummary(
            policyId="p1", name="policy", version="1", summary="test"
        )

        asyncio.run(refs.save_council(council))
        asyncio.run(refs.save_gate(gate))
        asyncio.run(refs.save_policy(policy))

        # Reconstruct fresh adapters to prove the state is not process-memory.
        fresh = governance_sqlite.SqliteGovernanceReferenceStore()
        assert asyncio.run(fresh.load_council()) == council
        assert asyncio.run(fresh.load_gates()) == [gate]
        assert asyncio.run(fresh.load_policies()) == [policy]
    finally:
        governance_sqlite.engine = original


def test_sqlite_governance_event_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'events.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE governance_events (id INTEGER PRIMARY KEY, candidate_id VARCHAR NOT NULL, event_type VARCHAR NOT NULL, payload TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE governance_audit (id INTEGER PRIMARY KEY, candidate_id VARCHAR NOT NULL, sequence INTEGER NOT NULL, event_type VARCHAR NOT NULL, payload TEXT NOT NULL, previous_hash VARCHAR NOT NULL, record_hash VARCHAR NOT NULL, signature VARCHAR NOT NULL, UNIQUE(candidate_id, sequence))"
        )

    original = governance_sqlite.engine
    governance_sqlite.engine = engine
    try:
        from app.core.contracts.governance import GovernanceDecision

        decision = GovernanceDecision(
            decisionId="d1",
            candidateId="c1",
            generation=1,
            verdict="approve",
            fromState="proposed",
            toState="evaluating",
            authorizesTransition=True,
            decidedBy=["m1"],
            rationale="r",
            evidenceRefs=[],
            decidedAt="2026-09-25T00:00:00+00:00",
        )
        event = GovernanceDecisionMade(decision=decision)
        store = governance_sqlite.SqliteGovernanceEventStore()
        asyncio.run(store.append("c1", [event]))

        fresh = governance_sqlite.SqliteGovernanceEventStore()
        loaded = asyncio.run(fresh.load("c1"))
        assert len(loaded) == 1
        assert loaded[0] == event
        assert type(loaded[0]).__name__ == "GovernanceDecisionMade"
    finally:
        governance_sqlite.engine = original
