"""Engineering quality profiles for technology-neutral software generation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Role = Literal["frontend", "backend", "fullstack"]

@dataclass(frozen=True)
class QualityObligation:
    obligation_id: str
    domain: str
    statement: str
    verification: str

@dataclass(frozen=True)
class EngineeringQualityProfile:
    role: Role
    obligations: tuple[QualityObligation, ...]

FRONTEND_OBLIGATIONS = (
 QualityObligation("FE-COR","correctness","UI state and user flows must remain coherent","state/flow tests"),
 QualityObligation("FE-A11Y","accessibility","interfaces must support accessible interaction","accessibility audit"),
 QualityObligation("FE-PERF","performance","rendering and interaction performance must meet requirements","performance tests"),
 QualityObligation("FE-SEC","security","client-side trust boundaries and sensitive data handling are explicit","security tests"),
 QualityObligation("FE-ERR","resilience","loading, empty, error and degraded states are designed","state coverage"),
 QualityObligation("FE-TEST","testability","critical behavior is independently verifiable","unit/integration/e2e tests"),
 QualityObligation("FE-MAINT","maintainability","components and state boundaries remain comprehensible","static/review analysis"),
 QualityObligation("FE-UX","usability","interaction design must serve the stated user goals","journey verification"),
)
BACKEND_OBLIGATIONS = (
 QualityObligation("BE-DOM","domain","business invariants are explicit and preserved","invariant tests"),
 QualityObligation("BE-DATA","data","data integrity and transaction semantics are explicit","database/integration tests"),
 QualityObligation("BE-API","api","external contracts are deterministic and versionable","contract tests"),
 QualityObligation("BE-SEC","security","authentication, authorization and trust boundaries are explicit","security tests"),
 QualityObligation("BE-REL","reliability","timeouts, retries, idempotency and recovery are deliberate","failure tests"),
 QualityObligation("BE-OBS","observability","important behavior produces actionable evidence","observability tests"),
 QualityObligation("BE-PERF","performance","latency, throughput and resource constraints are tested","load tests"),
 QualityObligation("BE-TEST","testability","critical behavior is reproducibly verifiable","unit/integration/property tests"),
 QualityObligation("BE-OPS","operability","configuration, health and graceful lifecycle are explicit","operational tests"),
)
FULLSTACK_OBLIGATIONS = (
 QualityObligation("FS-FLOW","system flow","user intent remains coherent from UI through runtime effect","end-to-end tests"),
 QualityObligation("FS-CONTRACT","contracts","frontend, API and backend share canonical contracts","contract verification"),
 QualityObligation("FS-DATA","data integrity","UI state cannot imply effects the backend did not commit","effect/integration tests"),
 QualityObligation("FS-SEC","security","security boundaries hold across client and server","cross-layer security tests"),
 QualityObligation("FS-RES","resilience","failure behavior remains coherent across layers","failure journeys"),
 QualityObligation("FS-OBS","observability","a production issue can be traced across layers","trace correlation tests"),
 QualityObligation("FS-DEPLOY","delivery","build/deploy/runtime artifacts remain compatible","deployment verification"),
 QualityObligation("FS-EVOLVE","evolution","changes preserve contracts and previously verified invariants","regression/evolution tests"),
)

def profile_for(role: Role) -> EngineeringQualityProfile:
    obligations = {"frontend": FRONTEND_OBLIGATIONS, "backend": BACKEND_OBLIGATIONS, "fullstack": FULLSTACK_OBLIGATIONS}[role]
    return EngineeringQualityProfile(role, obligations)
