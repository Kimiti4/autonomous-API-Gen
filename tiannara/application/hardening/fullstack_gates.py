"""Full-stack compiler hardening contracts.

Certification is based on observable gates across the generated system, not on
source emission alone. Each gate records status and evidence references.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

class GateStatus(str, Enum):
    PASS="pass"
    FAIL="fail"
    UNKNOWN="unknown"
    NOT_APPLICABLE="not_applicable"

@dataclass(frozen=True)
class HardeningGate:
    gate_id: str
    layer: str
    description: str
    required: bool = True

FULLSTACK_HARDENING_GATES = (
    HardeningGate("REQ-TRACE","requirements","Every implementation capability traces to ISR requirements."),
    HardeningGate("API-CONTRACT","api","API behavior matches the technology-neutral contract."),
    HardeningGate("BACKEND-BUILD","backend","Backend compiles/builds without unresolved errors."),
    HardeningGate("FRONTEND-BUILD","frontend","Frontend compiles/builds without unresolved errors."),
    HardeningGate("UNIT-TEST","verification","Unit tests pass."),
    HardeningGate("INTEGRATION-TEST","verification","Integration tests pass across API/backend/frontend boundaries."),
    HardeningGate("SECURITY","security","Required authentication, authorization, isolation and security checks pass."),
    HardeningGate("E2E","verification","Required end-to-end acceptance scenarios pass."),
    HardeningGate("DEPLOY-SMOKE","deployment","The generated deployment starts and responds correctly."),
    HardeningGate("RUNTIME-OBS","runtime","Runtime health and required behavior are observed in the running system."),
    HardeningGate("FAILURE-RECOVERY","runtime","Declared failure/recovery behavior is exercised where required."),
    HardeningGate("EVIDENCE","epistemic","Evidence is tied to real execution and provenance; simulation cannot substitute for runtime evidence."),
)

@dataclass(frozen=True)
class GateResult:
    gate_id: str
    status: GateStatus
    evidence_refs: tuple[str, ...] = ()
    detail: str = ""

def certify_hardening(results: Iterable[GateResult]) -> bool:
    observed={r.gate_id:r for r in results}
    return all(
        observed.get(g.gate_id, GateResult(g.gate_id, GateStatus.UNKNOWN)).status == GateStatus.PASS
        for g in FULLSTACK_HARDENING_GATES if g.required
    )
