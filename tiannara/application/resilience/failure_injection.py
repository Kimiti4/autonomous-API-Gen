"""35.2 Failure injection -- modifies environment, never verdict."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

class FailureKind(str, Enum):
    PROCESS_CRASH="process_crash"; DB_UNAVAILABLE="database_unavailable"; NETWORK_PARTITION="network_partition"
    TIMEOUT="dependency_timeout"; DISK_EXHAUSTION="disk_exhaustion"

@dataclass(frozen=True)
class InjectedFailure:
    failure_id: str; kind: FailureKind; target_env: str; evidence_ref: str

def inject_failure(environment: dict, kind: FailureKind, ledger: EvolutionLedger) -> InjectedFailure:
    # Modify environment, not verdict
    env_id = environment.get("env_id","env-1")
    failure_id = f"failure-{kind.value}-{canonical_hash(env_id)[:6]}"
    # Simulate environment modification
    environment["failed_kind"] = kind.value
    ev = EvolutionEvent(event_id=failure_id, evolution_id=env_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=env_id, payload={"kind": kind.value, "env_id": env_id})
    ref = ledger.append_event(ev, evolution_id=env_id)
    return InjectedFailure(failure_id, kind, env_id, ref)
