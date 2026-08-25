"""35.0 Resilience Contract -- frozen, hash-bound, ledger-anchored."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

CONTRACT_ID = "phase35-resilience-contract-001"
VERSION = "1.0.0"

RESILIENCE_DIMENSIONS = (
    "process_failures", "resource_failures", "infrastructure_failures",
    "distributed_failures", "deployment_failures", "temporal_failures",
    "observability", "recovery", "degradation", "consistency",
)

FAILURE_TAXONOMY = (
    "process_crash", "supervisor_restart", "crash_loop",
    "memory_exhaustion", "disk_exhaustion", "connection_pool_exhaustion",
    "database_unavailable", "cache_unavailable", "network_partition", "dependency_timeout",
    "duplicate_delivery", "stale_read", "split_brain", "leader_failure",
    "failed_deployment", "rollback_failure",
    "clock_skew", "timeout_cascade", "retry_storm",
)

@dataclass(frozen=True)
class ResilienceContract:
    contract_id: str; version: str
    resilience_dimensions: tuple[str,...]
    failure_taxonomy: tuple[str,...]
    recovery_deadline_ms: int
    allowable_data_loss: str
    consistency_requirement: str
    exit_threshold: float
    bounded_policy: str
    critical_policy: str
    content_hash: str

def contract_body(c: ResilienceContract) -> dict:
    return {
        "contract_id": c.contract_id, "version": c.version,
        "resilience_dimensions": list(c.resilience_dimensions),
        "failure_taxonomy": list(c.failure_taxonomy),
        "recovery_deadline_ms": c.recovery_deadline_ms,
        "allowable_data_loss": c.allowable_data_loss,
        "consistency_requirement": c.consistency_requirement,
        "exit_threshold": c.exit_threshold,
        "bounded_policy": c.bounded_policy,
        "critical_policy": c.critical_policy,
    }

def hash_canonical(obj): return canonical_hash(obj)

def build_resilience_contract(contract_id=CONTRACT_ID) -> ResilienceContract:
    tmp = ResilienceContract(contract_id, VERSION, RESILIENCE_DIMENSIONS, FAILURE_TAXONOMY, 30000, "zero_loss", "strong_consistency", 0.995, "BOUNDED_NEVER_RECOVERED", "CRITICAL_FAILED_NEVER_CERTIFIED", "")
    h = hash_canonical(contract_body(tmp))
    return ResilienceContract(contract_id, VERSION, RESILIENCE_DIMENSIONS, FAILURE_TAXONOMY, 30000, "zero_loss", "strong_consistency", 0.995, "BOUNDED_NEVER_RECOVERED", "CRITICAL_FAILED_NEVER_CERTIFIED", h)

RESILIENCE_CONTRACT = build_resilience_contract()

def register_resilience_contract(c: ResilienceContract, ledger: EvolutionLedger) -> str:
    body = contract_body(c)
    assert c.content_hash == hash_canonical(body), "hash mismatch"
    ev = EvolutionEvent(event_id=f"resilience-contract-{c.contract_id}", evolution_id=c.contract_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=c.contract_id, payload={"resilience_contract": body, "content_hash": c.content_hash})
    return ledger.append_event(ev, evolution_id=c.contract_id)
