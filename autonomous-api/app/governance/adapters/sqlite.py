"""SQLite-backed governance stores for the live API composition root.

The stores are intentionally boring: append-only governance events and
versioned reference rows live in the same durable database as evolution
state. Domain objects remain storage-agnostic; this adapter owns only
serialization and reconstruction.
"""
from __future__ import annotations

import json

from sqlalchemy import text

from app.core.governance.audit import AuditRecord, GovernanceAuditSigner, verify_chain
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
    """Durable append-only governance event store with signed audit envelopes."""

    def __init__(self, signing_key: str = "development-only-audit-key"):
        self._signer = GovernanceAuditSigner(signing_key)

    async def append(self, candidate_id: str, events: list) -> None:
        if not events:
            return
        with engine.begin() as connection:
            previous = connection.execute(
                text(
                    "SELECT sequence, record_hash FROM governance_audit "
                    "WHERE candidate_id = :candidate_id ORDER BY sequence DESC LIMIT 1"
                ),
                {"candidate_id": candidate_id},
            ).first()
            sequence = (previous[0] + 1) if previous else 1
            previous_hash = previous[1] if previous else ""
            for event in events:
                payload = _dump_event(event)
                event_type = type(event).__name__
                record_hash, signature = self._signer.sign(
                    candidate_id=candidate_id,
                    sequence=sequence,
                    event_type=event_type,
                    payload=payload,
                    previous_hash=previous_hash,
                )
                connection.execute(
                    text(
                        "INSERT INTO governance_events "
                        "(candidate_id, event_type, payload) "
                        "VALUES (:candidate_id, :event_type, :payload)"
                    ),
                    {
                        "candidate_id": candidate_id,
                        "event_type": event_type,
                        "payload": payload,
                    },
                )
                connection.execute(
                    text(
                        "INSERT INTO governance_audit "
                        "(candidate_id, sequence, event_type, payload, previous_hash, record_hash, signature) "
                        "VALUES (:candidate_id, :sequence, :event_type, :payload, "
                        ":previous_hash, :record_hash, :signature)"
                    ),
                    {
                        "candidate_id": candidate_id,
                        "sequence": sequence,
                        "event_type": event_type,
                        "payload": payload,
                        "previous_hash": previous_hash,
                        "record_hash": record_hash,
                        "signature": signature,
                    },
                )
                previous_hash = record_hash
                sequence += 1

    async def audit(self, candidate_id: str) -> list[AuditRecord]:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT candidate_id, sequence, event_type, payload, previous_hash, "
                    "record_hash, signature FROM governance_audit "
                    "WHERE candidate_id = :candidate_id ORDER BY sequence ASC"
                ),
                {"candidate_id": candidate_id},
            ).all()
            event_count = connection.execute(
                text(
                    "SELECT COUNT(*) FROM governance_events "
                    "WHERE candidate_id = :candidate_id"
                ),
                {"candidate_id": candidate_id},
            ).scalar_one()
        records = [AuditRecord(*row) for row in rows]
        if len(records) != event_count:
            raise RuntimeError(
                "governance audit/event count mismatch; refusing unsigned or incomplete history"
            )
        verify_chain(records, self._signer)
        return records

    async def load(self, candidate_id: str) -> list:
        records = await self.audit(candidate_id)
        return [_load_event(record.payload) for record in records]


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
