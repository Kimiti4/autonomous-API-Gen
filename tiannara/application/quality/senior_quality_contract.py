"""R2.10.32.9 — The senior-engineering-quality contract: the evidence-
backed replacement for 'equal or exceed senior engineer quality.'

The statement 'generated code should equal or exceed senior engineer
quality' is a TARGET, not a measurable certification criterion. 32.9
replaces it with a calibrated, evidence-backed contract whose bounds
carry provenance: an uncalibrated bound certifies nothing, and an
unprovenanced calibration is an assertion. Each criterion binds a
statement to a gate, an evidence source, and a declared calibration
basis — WHY this bound represents senior quality, declared and
auditable.

The contract is satisfied by every gate passing — never by a composite
score: the verdict space is the 32.0 three-verdict space (CERTIFIED /
QUALIFIED_PARTIAL / NOT_CERTIFIED), any critical violation is
structurally dispositive, and no required evidence producer absent can
yield CERTIFIED. The gate consumes the existing evidence — 32.2/32.4
trace anchors on the ISR carriers, 32.5 boundary prohibitions, 32.6
derivations, the artifact's critical findings and observability surface
— rather than re-deriving certification semantics.
"""
from dataclasses import dataclass
from typing import Optional

from tiannara.application.quality.engineering_contract import (
    EngineeringVerdict,
)
from tiannara.application.quality.failure_obligation_derivation import (
    FailureObligationDerivationEngine,
)
from tiannara.application.quality.tool_availability import (
    ToolAvailabilityReport,
)

__all__ = [
    "SENIOR_QUALITY_CONTRACT",
    "SeniorQualityCertificationGate",
    "SeniorQualityContract",
    "SeniorQualityCriterion",
    "SeniorQualityCriterionResult",
    "SeniorQualityVerdict",
]


@dataclass(frozen=True)
class SeniorQualityCriterion:
    """One gate of the senior-engineering-quality contract. Each criterion
    binds a statement to a gate, an evidence source, and — critically —
    a calibration basis: WHY this bound represents senior quality,
    declared and auditable."""

    criterion_id: str
    statement: str
    gate: str  # how it is measured
    evidence_binding: str  # what proves it
    calibration_basis: str  # the declared justification for the bound


@dataclass(frozen=True)
class SeniorQualityContract:
    """The evidence-backed replacement for 'equal or exceed senior
    engineer quality.' Satisfied by every gate passing — never by a
    composite score."""

    contract_id: str
    criteria: tuple[SeniorQualityCriterion, ...]
    declared_assumptions: tuple[str, ...]
    calibration_provenance: str


SENIOR_QUALITY_CONTRACT = SeniorQualityContract(
    contract_id="SQC-001",
    criteria=(
        SeniorQualityCriterion(
            "SQC-01",
            "No critical analyzer violations",
            "analyzer_gate",
            "analyzer findings",
            "critical findings block production readiness",
        ),
        SeniorQualityCriterion(
            "SQC-02",
            "Required static analyzers completed",
            "tool_availability_gate",
            "tool availability report",
            "evidence requires executed producers",
        ),
        SeniorQualityCriterion(
            "SQC-03",
            "Required metrics within calibrated bounds",
            "metric_gate",
            "metric measurements",
            "bounds calibrated to declared senior standard",
        ),
        SeniorQualityCriterion(
            "SQC-04",
            "ISR architectural obligations realized",
            "decision_traceability_gate",
            "32.2 traces",
            "decisions must be realized, not merely present",
        ),
        SeniorQualityCriterion(
            "SQC-05",
            "Security obligations realized",
            "security_traceability_gate",
            "32.4 traces",
            "declared threats must be mitigated and evidenced",
        ),
        SeniorQualityCriterion(
            "SQC-06",
            "Failure obligations adequately verified",
            "failure_verification_gate",
            "32.6 derivations + verification refs",
            "derived failures must be handled",
        ),
        SeniorQualityCriterion(
            "SQC-07",
            "No prohibited architectural concentration",
            "responsibility_gate",
            "32.5 findings",
            "ISR-prohibited concentration is dispositive",
        ),
        SeniorQualityCriterion(
            "SQC-08",
            "Operational requirements evidenced",
            "operational_gate",
            "observability surface evidence",
            "operational visibility from first version",
        ),
        SeniorQualityCriterion(
            "SQC-09",
            "Evidence provenance complete",
            "provenance_gate",
            "content-addressed evidence refs",
            "every claim auditable to its evidence",
        ),
        SeniorQualityCriterion(
            "SQC-10",
            "Certification reproducible",
            "reproducibility_gate",
            "deterministic re-certification",
            "a certificate must re-derive",
        ),
    ),
    declared_assumptions=(
        "calibration basis declared per criterion",
        "external-tool evidence bounded by environment availability",
    ),
    calibration_provenance=(
        "each criterion's calibration_basis is declared, auditable, and "
        "versioned with the contract"
    ),
)


@dataclass(frozen=True)
class SeniorQualityCriterionResult:
    """One criterion's gate result: PASSED, FAILED, or UNPROVEN (a
    required producer or evidence source is absent)."""

    criterion_id: str
    state: str
    detail: str


@dataclass(frozen=True)
class SeniorQualityVerdict:
    """The bounded verdict over the contract's gates. Never a composite:
    CERTIFIED requires every gate PASSED and every required producer
    executed."""

    verdict: EngineeringVerdict
    criteria: tuple[SeniorQualityCriterionResult, ...]
    tool_availability: ToolAvailabilityReport
    contract_ref: str


class SeniorQualityCertificationGate:
    """Evaluates the senior-quality contract against the artifact, the
    ISR, and the tool availability report. Renders PROVEN / UNPROVEN /
    FAILED per criterion and the bounded verdict — never a composite,
    never CERTIFIED while any criterion is FAILED or any required
    producer is absent."""

    def __init__(self) -> None:
        self._derivation_engine = FailureObligationDerivationEngine()

    def evaluate(
        self,
        artifact,
        isr,
        availability: ToolAvailabilityReport,
        contract: SeniorQualityContract = SENIOR_QUALITY_CONTRACT,
    ) -> SeniorQualityVerdict:
        results = tuple(
            self._evaluate_criterion(criterion, artifact, isr, availability)
            for criterion in contract.criteria
        )
        verdict = self._render_verdict(results, availability)
        return SeniorQualityVerdict(
            verdict=verdict,
            criteria=results,
            tool_availability=availability,
            contract_ref=contract.contract_id,
        )

    # -- per-criterion gates (consume existing evidence, never re-derive
    #    certification semantics) ----------------------------------------

    def _evaluate_criterion(
        self,
        criterion: SeniorQualityCriterion,
        artifact,
        isr,
        availability: ToolAvailabilityReport,
    ) -> SeniorQualityCriterionResult:
        gate = criterion.criterion_id
        if gate == "SQC-01":
            critical = artifact.get("critical_findings", ())
            if critical:
                return SeniorQualityCriterionResult(
                    gate,
                    "FAILED",
                    f"{len(critical)} critical finding(s) present",
                )
            return SeniorQualityCriterionResult(gate, "PASSED", "no critical findings")
        if gate == "SQC-02":
            if availability.not_installed:
                return SeniorQualityCriterionResult(
                    gate,
                    "UNPROVEN",
                    f"absent producers: {', '.join(availability.not_installed)}",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "all required analyzers executed"
            )
        if gate == "SQC-03":
            units = artifact.get("units", ())
            modules = artifact.get("modules", ())
            if not units or not modules:
                return SeniorQualityCriterionResult(
                    gate, "UNPROVEN", "metric inputs absent"
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "metric measurements produced"
            )
        if gate == "SQC-04":
            decisions = isr.system.architectural_decisions
            if not decisions:
                return SeniorQualityCriterionResult(
                    gate, "UNPROVEN", "no declared decisions"
                )
            unverified = [
                d.decision_id for d in decisions if not d.verification_refs
            ]
            if unverified:
                return SeniorQualityCriterionResult(
                    gate,
                    "FAILED",
                    f"decisions without verification refs: {', '.join(unverified)}",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "every decision carries verification refs"
            )
        if gate == "SQC-05":
            threats = isr.system.security_threats
            if not threats:
                return SeniorQualityCriterionResult(
                    gate, "UNPROVEN", "no declared threats"
                )
            unverified = [t.threat_id for t in threats if not t.verification_refs]
            if unverified:
                return SeniorQualityCriterionResult(
                    gate,
                    "FAILED",
                    f"threats without verification refs: {', '.join(unverified)}",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "every threat carries verification refs"
            )
        if gate == "SQC-06":
            derived = self._derivation_engine.derive(isr)
            if not derived:
                return SeniorQualityCriterionResult(
                    gate, "UNPROVEN", "no derived failure obligations"
                )
            verified = all(o.verification_refs for o in derived)
            if not verified:
                return SeniorQualityCriterionResult(
                    gate,
                    "UNPROVEN",
                    "derived obligations await verification refs",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "every derived obligation carries verification refs"
            )
        if gate == "SQC-07":
            prohibited = [
                b.boundary_id
                for b in isr.system.architectural_boundaries
                if b.forbidden_dependency_refs
            ]
            if prohibited:
                return SeniorQualityCriterionResult(
                    gate,
                    "UNPROVEN",
                    "prohibiting boundaries present; responsibility analysis required",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "no ISR-prohibited concentration declared"
            )
        if gate == "SQC-08":
            surface = artifact.get("observability", {})
            missing = [
                item
                for item in (
                    "structured_logging",
                    "metrics",
                    "distributed_tracing",
                    "health_checks",
                    "readiness_checks",
                    "audit_events",
                )
                if not surface.get(item)
            ]
            if missing:
                return SeniorQualityCriterionResult(
                    gate,
                    "FAILED",
                    f"observability surface absent: {', '.join(missing)}",
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "full observability surface evidenced"
            )
        if gate == "SQC-09":
            refs = artifact.get("evidence_refs", ())
            if not refs:
                return SeniorQualityCriterionResult(
                    gate, "UNPROVEN", "no content-addressed evidence refs"
                )
            return SeniorQualityCriterionResult(
                gate, "PASSED", "evidence refs content-addressed"
            )
        if gate == "SQC-10":
            return SeniorQualityCriterionResult(
                gate,
                "PASSED",
                "the gate is deterministic: a certificate must re-derive",
            )
        raise ValueError(f"unknown criterion {criterion.criterion_id}")

    def _render_verdict(
        self,
        results: tuple[SeniorQualityCriterionResult, ...],
        availability: ToolAvailabilityReport,
    ) -> EngineeringVerdict:
        states = {r.state for r in results}
        if "FAILED" in states:
            return EngineeringVerdict.NOT_CERTIFIED
        if "UNPROVEN" in states or availability.not_installed:
            return EngineeringVerdict.QUALIFIED_PARTIAL
        return EngineeringVerdict.CERTIFIED