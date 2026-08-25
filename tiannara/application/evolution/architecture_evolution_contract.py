"""34.0 Architecture Evolution Contract -- frozen, hash-bound."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

class EvolutionState(str, Enum):
    PROPOSED = "PROPOSED"; SIMULATED = "SIMULATED"; VERIFIED = "VERIFIED"; ADOPTED = "ADOPTED"; REJECTED = "REJECTED"; BOUNDED = "BOUNDED"

@dataclass(frozen=True)
class ArchitectureEvolutionContract:
    contract_id: str
    architecture_dimensions: tuple[str,...]
    scalability_dimensions: tuple[str,...]
    reliability_dimensions: tuple[str,...]
    latency_constraints: tuple[str,...]
    throughput_constraints: tuple[str,...]
    consistency_requirements: tuple[str,...]
    availability_requirements: tuple[str,...]
    cost_constraints: tuple[str,...]
    deployment_constraints: tuple[str,...]
    migration_constraints: tuple[str,...]
    rollback_requirements: tuple[str,...]
    semantic_preservation_requirements: tuple[str,...]
    content_hash: str

def contract_body(c: ArchitectureEvolutionContract) -> dict:
    return {
        "contract_id": c.contract_id,
        "architecture_dimensions": list(c.architecture_dimensions),
        "scalability_dimensions": list(c.scalability_dimensions),
        "reliability_dimensions": list(c.reliability_dimensions),
        "latency_constraints": list(c.latency_constraints),
        "throughput_constraints": list(c.throughput_constraints),
        "consistency_requirements": list(c.consistency_requirements),
        "availability_requirements": list(c.availability_requirements),
        "cost_constraints": list(c.cost_constraints),
        "deployment_constraints": list(c.deployment_constraints),
        "migration_constraints": list(c.migration_constraints),
        "rollback_requirements": list(c.rollback_requirements),
        "semantic_preservation_requirements": list(c.semantic_preservation_requirements),
    }

def build_architecture_evolution_contract(contract_id="arch-evolution-001") -> ArchitectureEvolutionContract:
    tmp = ArchitectureEvolutionContract(
        contract_id, ("services","databases","queues","caches"), ("throughput","latency"), ("availability","failure_recovery"),
        ("p99<200ms",), ("10k rps",), ("strong_consistency",), ("99.99%",), ("cost<budget",), ("multi_region",), ("zero_downtime",), ("rollback_verified",), ("intent_preserved",), ""
    )
    h = canonical_hash(contract_body(tmp))
    return ArchitectureEvolutionContract(tmp.contract_id, tmp.architecture_dimensions, tmp.scalability_dimensions, tmp.reliability_dimensions, tmp.latency_constraints, tmp.throughput_constraints, tmp.consistency_requirements, tmp.availability_requirements, tmp.cost_constraints, tmp.deployment_constraints, tmp.migration_constraints, tmp.rollback_requirements, tmp.semantic_preservation_requirements, h)

ARCHITECTURE_EVOLUTION_CONTRACT = build_architecture_evolution_contract()

def register_architecture_contract(c: ArchitectureEvolutionContract, ledger: EvolutionLedger) -> str:
    body = contract_body(c)
    assert c.content_hash == canonical_hash(body), "hash mismatch"
    assert EvolutionState.BOUNDED != EvolutionState.ADOPTED
    ev = EvolutionEvent(event_id=f"arch-contract-{c.contract_id}", evolution_id=c.contract_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=c.contract_id, payload={"arch_contract": body, "content_hash": c.content_hash})
    return ledger.append_event(ev, evolution_id=c.contract_id)
