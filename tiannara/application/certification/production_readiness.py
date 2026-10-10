"""Production Readiness -- thin conjunction, no scoring, no mutation."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash
from tiannara.application.hardening.fullstack_gates import GateResult
from tiannara.application.certification.hardening_certification import certify_generated_application

class DimensionVerdict(str, Enum):
    CERTIFIED = "CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    BOUNDED = "BOUNDED"
    NOT_TESTED = "NOT_TESTED"

class ProductionReadinessVerdict(str, Enum):
    PRODUCTION_READY = "PRODUCTION_READY"
    NOT_PRODUCTION_READY = "NOT_PRODUCTION_READY"

REQUIRED_DIMENSIONS = ("compiler", "engineering", "security", "resilience")

@dataclass(frozen=True)
class CertificationEvidence:
    dimension: str
    verdict: DimensionVerdict
    critical_violations: int
    evidence_refs: tuple[str, ...]
    content_hash: str

@dataclass(frozen=True)
class BlockingDimension:
    dimension: str
    reason: str

@dataclass(frozen=True)
class ProductionReadinessResult:
    verdict: ProductionReadinessVerdict
    blocking_dimensions: tuple[BlockingDimension, ...]
    evidence_refs: tuple[str, ...]
    readiness_event_ref: str

class ProductionReadinessGate:
    def __init__(self, ledger: EvolutionLedger):
        self.ledger = ledger
        self._ledger = ledger

    def ledger_event_by_ref(self, ref): return self.ledger.event_by_ref(ref)
    def verify_event_chain(self): return self.ledger.verify_event_chain()
    def matrix_summary(self):
        from tests.test_r29_10_9_campaign_readiness import CampaignReadinessHarness
        h = CampaignReadinessHarness()
        return h.matrix_summary()
    def recipe_isr_hash(self):
        from tests.test_r29_10_9_campaign_readiness import CampaignReadinessHarness
        h = CampaignReadinessHarness()
        return h.recipe_isr_hash()

    def evaluate_generated_application(
        self,
        evidence: Mapping[str, CertificationEvidence],
        *,
        compilation_ok: bool,
        hardening_results: tuple[GateResult, ...] | list[GateResult],
    ) -> ProductionReadinessResult:
        """Evaluate production readiness with the full-stack hardening boundary.

        The existing dimension conjunction remains necessary. The generated
        application is additionally blocked unless every required hardening
        gate has real PASS evidence.
        """
        readiness = self.evaluate(evidence)
        hardening = certify_generated_application(
            compilation_ok=compilation_ok,
            gate_results=hardening_results,
        )
        if hardening.certified:
            return readiness

        blockers = list(readiness.blocking_dimensions)
        blockers.append(
            BlockingDimension(
                "fullstack-hardening",
                ";".join(hardening.blockers) or "NOT_CERTIFIED",
            )
        )
        return ProductionReadinessResult(
            ProductionReadinessVerdict.NOT_PRODUCTION_READY,
            tuple(blockers),
            readiness.evidence_refs,
            readiness.readiness_event_ref,
        )

    def evaluate(self, evidence: Mapping[str, CertificationEvidence]) -> ProductionReadinessResult:
        blockers = []
        resolved_refs = []
        for dim in REQUIRED_DIMENSIONS:
            ev = evidence.get(dim)
            if ev is None:
                blockers.append(BlockingDimension(dim, "ABSENT"))
                continue
            # Check evidence resolves
            if not all(self._ledger.event_by_ref(r) is not None for r in ev.evidence_refs):
                blockers.append(BlockingDimension(dim, "UNRESOLVED_EVIDENCE"))
                continue
            resolved_refs.extend(ev.evidence_refs)
            if ev.critical_violations > 0:
                blockers.append(BlockingDimension(dim, "CRITICAL_VIOLATION"))
                continue
            if ev.verdict is not DimensionVerdict.CERTIFIED:
                blockers.append(BlockingDimension(dim, ev.verdict.value))
        verdict = ProductionReadinessVerdict.PRODUCTION_READY if not blockers else ProductionReadinessVerdict.NOT_PRODUCTION_READY
        # Record readiness event
        payload = {"verdict": verdict.value, "blocking": [(b.dimension, b.reason) for b in blockers], "evidence_refs": list(resolved_refs)}
        ev = EvolutionEvent(event_id=f"production-readiness-{canonical_hash(payload)[:8]}", evolution_id="readiness", sequence=0, event_type=EventType.CERTIFICATION, subject_id="readiness", payload=payload)
        ref = self._ledger.append_event(ev, evolution_id="readiness")
        return ProductionReadinessResult(verdict, tuple(blockers), tuple(resolved_refs), ref)

    def record_readiness(self, verdict, blockers, refs):
        payload = {"verdict": verdict.value, "blocking": [(b.dimension, b.reason) for b in blockers], "evidence_refs": list(refs)}
        ev = EvolutionEvent(event_id=f"production-readiness-{canonical_hash(payload)[:8]}", evolution_id="readiness", sequence=0, event_type=EventType.CERTIFICATION, subject_id="readiness", payload=payload)
        return self._ledger.append_event(ev, evolution_id="readiness")
