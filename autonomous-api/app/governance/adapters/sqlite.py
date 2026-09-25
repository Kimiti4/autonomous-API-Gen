"""SQLite-backed governance stores for the live API composition root.

The stores are intentionally boring: append-only governance events and
versioned reference rows live in the same durable database as evolution
state. Domain objects remain storage-agnostic; this adapter owns only
serialization and reconstruction.
"""
from __future__ import annotations

import json

from sqlalchemy import text

from app.core.contracts.governance import (
    CouncilComposition,
    GovernanceGate,
    PolicySummary,
)
from app.core.governance.events import (
    CertificationGranted,
    CertificationRevoked,
    CouncilUpdated,
    GateEvaluated,
    GateRegistered,
    GovernanceDecisionMade,
    PolicyRegistered,
)
from app.storage.db import engine

_EVENT_TYPES = {
    cls.__name__: cls
    for cls in (
        GovernanceDecisionMade,
        GateEvaluated,
        CertificationGranted,
        CertificationRevoked,
        CouncilUpdated,
        GateRegistered,
        PolicyRegistered,
    )
}


def _dump_event(event) -> str:
    return json.dumps(
        {"type": type(event).__name__, "payload": event.model_dump(mode="json")},
        sort_keys=True,
        separators=(",", ":"),
    )


def _load_event(raw: str):
    record = json.loads(raw)
    event_type = record.get("type")
    cls = _EVENT_TYPES.get(event_type)
    if cls is None:
        raise RuntimeError(f"unknown persisted governance event type: {event_type}")
    return cls.model_validate(record["payload"])


class SqliteGovernanceEventStore:
    """Durable append-only governance event store."""

    async def append(self, candidate_id: str, events: list) -> None:
        if not events:
            return
        with engine.begin() as connection:
            for event in events:
                connection.execute(
                    text(
                        "INSERT INTO governance_events "
                        "(candidate_id, event_type, payload) "
                        "VALUES (:candidate_id, :event_type, :payload)"
                    ),
                    {
                        "candidate_id": candidate_id,
                        "event_type": type(event).__name__,
                        "payload": _dump_event(event),
                    },
                )

    async def load(self, candidate_id: str) -> list:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT payload FROM governance_events "
                    "WHERE candidate_id = :candidate_id ORDER BY id ASC"
                ),
                {"candidate_id": candidate_id},
            ).scalars().all()
        return [_load_event(raw) for raw in rows]

    async def load_generation(self, generation: int) -> dict:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT candidate_id, payload FROM governance_events "
                    "WHERE event_type = 'GovernanceDecisionMade' ORDER BY id ASC"
                )
            ).all()

        result = {}
        for candidate_id, raw in rows:
            event = _load_event(raw)
            if event.decision.generation == generation:
                result.setdefault(candidate_id, []).append(event)

        # A generation projection needs the complete candidate history so
        # lifecycle state is reconstructed correctly, not just the matching
        # decision event.
        complete = {}
        for candidate_id in result:
            complete[candidate_id] = await self.load(candidate_id)
        return complete


class SqliteGovernanceReferenceStore:
    """Durable council/gate/policy registry."""

    async def save_council(self, composition: CouncilComposition) -> None:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM governance_council"))
            connection.execute(
                text(
                    "INSERT INTO governance_council (registry_key, payload) "
                    "VALUES ('current', :payload)"
                ),
                {"payload": composition.model_dump_json()},
            )

    async def load_council(self):
        with engine.connect() as connection:
            raw = connection.execute(
                text(
                    "SELECT payload FROM governance_council "
                    "WHERE registry_key = 'current'"
                )
            ).scalar_one_or_none()
        return CouncilComposition.model_validate_json(raw) if raw else None

    async def save_gate(self, gate: GovernanceGate) -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO governance_gates (gate_id, payload) "
                    "VALUES (:gate_id, :payload) "
                    "ON CONFLICT(gate_id) DO UPDATE SET payload = excluded.payload"
                ),
                {"gate_id": gate.gateId, "payload": gate.model_dump_json()},
            )

    async def load_gates(self) -> list:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT payload FROM governance_gates ORDER BY gate_id")
            ).scalars().all()
        return [GovernanceGate.model_validate_json(raw) for raw in rows]

    async def save_policy(self, policy: PolicySummary) -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO governance_policies (policy_id, payload) "
                    "VALUES (:policy_id, :payload) "
                    "ON CONFLICT(policy_id) DO UPDATE SET payload = excluded.payload"
                ),
                {"policy_id": policy.policyId, "payload": policy.model_dump_json()},
            )

    async def load_policies(self) -> list:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT payload FROM governance_policies ORDER BY policy_id")
            ).scalars().all()
        return [PolicySummary.model_validate_json(raw) for raw in rows]
