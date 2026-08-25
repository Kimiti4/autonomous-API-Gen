"""35.0 Chaos Contract -- frozen, hash-bound."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

@dataclass(frozen=True)
class ChaosContract:
    contract_id: str
    failure_classes: tuple[str,...]
    blast_radius: str
    injection_policy: str
    recovery_deadline_ms: int
    critical_failures: tuple[str,...]
    acceptable_degradation: str
    containment_requirement: str
    content_hash: str

def contract_body(c: ChaosContract) -> dict:
    return {"contract_id": c.contract_id, "failure_classes": list(c.failure_classes), "blast_radius": c.blast_radius, "injection_policy": c.injection_policy, "recovery_deadline_ms": c.recovery_deadline_ms, "critical_failures": list(c.critical_failures)}

def build_chaos_contract(contract_id="chaos-contract-001") -> ChaosContract:
    tmp = ChaosContract(contract_id, ("container_death","network_partition","database_deletion","clock_skew","api_failure"), "single_az", "controlled", 30000, ("database_deletion","split_brain"), "degraded_throughput", "", "")
    h = canonical_hash(contract_body(tmp))
    return ChaosContract(tmp.contract_id, tmp.failure_classes, tmp.blast_radius, tmp.injection_policy, tmp.recovery_deadline_ms, tmp.critical_failures, tmp.acceptable_degradation, "", h)

CHAOS_CONTRACT = build_chaos_contract()

def register_chaos_contract(c: ChaosContract, ledger: EvolutionLedger) -> str:
    body = contract_body(c)
    assert c.content_hash == canonical_hash(body), "hash mismatch"
    ev = EvolutionEvent(event_id=f"chaos-contract-{c.contract_id}", evolution_id=c.contract_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=c.contract_id, payload={"chaos_contract": body, "content_hash": c.content_hash})
    return ledger.append_event(ev, evolution_id=c.contract_id)
