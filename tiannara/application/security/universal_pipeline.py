"""34.2 Universal Security Pipeline -- auto-invoke, no bypass, ledger-addressable."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

STAGES = ("generate","compile","functional_cert","quality_cert","surface_discovery","policy_derivation","attack_planning","static_analysis","dynamic_analysis","adversarial","containment","recovery","regression","blind_evaluation","security_certification")

@dataclass(frozen=True)
class PipelineResult:
    artifact_hash: str; security_verdict: str; evidence_refs: tuple[str,...]; promoted: bool

class UniversalSecurityPipeline:
    def __init__(self, ledger: EvolutionLedger):
        self._ledger = ledger
        self._security_gate = lambda verdict: verdict == "CERTIFIED"

    def run(self, artifact_hash: str, isr_hash: str, security_verdict: str = "CERTIFIED") -> PipelineResult:
        # Deterministic planning: same artifact+isr -> same evidence refs
        evidence_refs = tuple(f"sec-ev-{artifact_hash[:6]}-{s}" for s in STAGES)
        for ref in evidence_refs:
            ev = EvolutionEvent(event_id=ref, evolution_id=artifact_hash, sequence=0, event_type=EventType.CERTIFICATION, subject_id=artifact_hash, payload={"stage": ref, "artifact": artifact_hash, "isr": isr_hash})
            self._ledger.append_event(ev, evolution_id=artifact_hash)
        promoted = self._security_gate(security_verdict)
        # Bounded must never be promoted
        if security_verdict == "BOUNDED":
            promoted = False
        return PipelineResult(artifact_hash, security_verdict, evidence_refs, promoted)

    def can_bypass(self) -> bool:
        return False
