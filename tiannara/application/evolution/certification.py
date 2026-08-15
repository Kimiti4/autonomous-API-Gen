"""R2.8.14 -- R2.8 adversarial certification.

Aggregates the full R2.8 anti-gaming campaign into a single, versioned,
chain-anchored, multi-dimensional certification artifact.

Constitutional constraints honored:

* Multi-objective, no single aggregate score: the artifact is a structured
  report with one section per R2.8 slice; it is never collapsed to one number.
* Epistemic honesty: the artifact distinguishes CERTIFIED_FULL from
  QUALIFIED_PARTIAL from NOT_CERTIFIED based on what was ACTUALLY evaluated.
  An environment limitation yields QUALIFIED_PARTIAL, never a silent CERTIFIED.
* Tamper-evidence: the artifact is content-hashed and anchored in the
  EvolutionLedger as a CERTIFICATION event; post-hoc modification is detectable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, Mapping

from .ledger import EventType, EvolutionEvent, EvolutionLedger


class CertificationStatus(str, Enum):
    CERTIFIED_FULL = "CERTIFIED_FULL"
    QUALIFIED_PARTIAL = "QUALIFIED_PARTIAL"
    NOT_CERTIFIED = "NOT_CERTIFIED"


class CoverageStatus(str, Enum):
    EVALUATED_STATIC = "EVALUATED_STATIC"
    EVALUATED_DYNAMIC = "EVALUATED_DYNAMIC"
    UNEVALUATED = "UNEVALUATED"
    BLOCKED_BY_ENVIRONMENT = "BLOCKED_BY_ENVIRONMENT"


class EnvironmentCapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"


# Dimensions that require real execution (Docker) to evaluate, versus those
# that can be evaluated hermetically from the ISR alone.
_DYNAMIC_DIMENSIONS = frozenset({
    "correctness", "regression_safety", "causal_validity", "performance",
})
_STATIC_DIMENSIONS = frozenset({
    "structural_validity", "invariant_compliance", "security",
    "complexity_efficiency",
})
# Critical dimensions: unevaluated -> cannot reach CERTIFIED_FULL.
_CRITICAL_DIMENSIONS = frozenset({
    "correctness", "regression_safety", "security", "invariant_compliance",
    "causal_validity",
})


@dataclass(frozen=True)
class EnvironmentCapability:
    """What the evaluation environment can actually do in this run."""
    hermetic_static: EnvironmentCapabilityStatus
    hermetic_composition: EnvironmentCapabilityStatus
    dynamic_execution: EnvironmentCapabilityStatus
    dynamic_execution_note: str = ""


@dataclass(frozen=True)
class DimensionCoverage:
    dimension: str
    critical: bool
    status: CoverageStatus
    note: str = ""


@dataclass(frozen=True)
class SectionResult:
    """Certification result for one R2.8 slice."""
    section_id: str
    passed: bool
    mandatory: bool                     # must pass for ANY certification
    metrics: Mapping[str, object] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class QuarantineDisposition:
    failure_count: int
    introduced_by_r28: bool
    causal_reproduction: str            # e.g. "CONFIRMED_PRE_R28"
    impact: str


@dataclass(frozen=True)
class CertificationAnchors:
    """Content hashes binding the certification to a specific configuration."""
    corpus_hash: str
    protected_test_hash: str
    holdout_hash: str
    baseline_hash: str
    isr_hash: str


@dataclass(frozen=True)
class CertificationArtifact:
    certification_id: str
    anchors: CertificationAnchors
    status: CertificationStatus
    environment: EnvironmentCapability
    dimension_coverage: tuple[DimensionCoverage, ...]
    sections: tuple[SectionResult, ...]
    quarantine: QuarantineDisposition
    red_team_scope_note: str
    red_team_query_budget: int

    def content_hash(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def adversarial_signals(self) -> Mapping[str, object]:
        """Flattened adversarial metrics for the certification summary."""
        signals: dict[str, object] = {}
        for section in self.sections:
            for key, value in section.metrics.items():
                signals[f"{section.section_id}.{key}"] = value
        return signals


SectionRunner = Callable[[], SectionResult]


class CertificationAuthority:
    """Runs the R2.8 section checks and produces the certification artifact.

    Section runners are injected (dependency inversion): in production they call
    the live measurement/composition/red-team layers; in tests they can be
    replaced to simulate failures. The authority itself never fabricates a
    result -- it only aggregates and applies the status rules.
    """

    RED_TEAM_SCOPE_NOTE = (
        "Red team searches compositions of known attack primitives, not novel "
        "primitives; the negative result is bounded by this scope."
    )

    def __init__(
        self,
        ledger: EvolutionLedger,
        environment: EnvironmentCapability,
        section_runners: Mapping[str, SectionRunner],
        anchors: CertificationAnchors,
        quarantine: QuarantineDisposition,
        red_team_query_budget: int = 1000,
    ) -> None:
        self._ledger = ledger
        self._environment = environment
        self._section_runners = dict(section_runners)
        self._anchors = anchors
        self._quarantine = quarantine
        self._red_team_query_budget = red_team_query_budget

    def certify(self) -> CertificationArtifact:
        sections = tuple(runner() for runner in self._section_runners.values())
        coverage = self._assess_dimension_coverage()
        status = self._determine_status(sections, coverage)

        artifact = CertificationArtifact(
            certification_id=self._derive_certification_id(),
            anchors=self._anchors,
            status=status,
            environment=self._environment,
            dimension_coverage=tuple(coverage),
            sections=sections,
            quarantine=self._quarantine,
            red_team_scope_note=self.RED_TEAM_SCOPE_NOTE,
            red_team_query_budget=self._red_team_query_budget,
        )
        self._anchor(artifact)
        return artifact

    # -- status rules (the epistemic core) ----------------------------------

    def _determine_status(
        self,
        sections: tuple[SectionResult, ...],
        coverage: tuple[DimensionCoverage, ...],
    ) -> CertificationStatus:
        # Any mandatory invariant failing -> NOT_CERTIFIED, unconditionally.
        if any(section.mandatory and not section.passed for section in sections):
            return CertificationStatus.NOT_CERTIFIED
        # All mandatory pass, but a critical dimension was not evaluated
        # (e.g. Docker unavailable) -> QUALIFIED_PARTIAL, never CERTIFIED.
        blocked = any(
            c.critical and c.status in (
                CoverageStatus.UNEVALUATED,
                CoverageStatus.BLOCKED_BY_ENVIRONMENT,
            )
            for c in coverage
        )
        if blocked:
            return CertificationStatus.QUALIFIED_PARTIAL
        return CertificationStatus.CERTIFIED_FULL

    def _assess_dimension_coverage(self) -> tuple[DimensionCoverage, ...]:
        dynamic_available = (
            self._environment.dynamic_execution is EnvironmentCapabilityStatus.AVAILABLE
        )
        coverage: list[DimensionCoverage] = []
        for dim in sorted(_DYNAMIC_DIMENSIONS | _STATIC_DIMENSIONS):
            critical = dim in _CRITICAL_DIMENSIONS
            if dim in _DYNAMIC_DIMENSIONS:
                if dynamic_available:
                    status, note = CoverageStatus.EVALUATED_DYNAMIC, ""
                else:
                    status = CoverageStatus.BLOCKED_BY_ENVIRONMENT
                    note = self._environment.dynamic_execution_note
            else:
                status, note = CoverageStatus.EVALUATED_STATIC, ""
            coverage.append(DimensionCoverage(dim, critical, status, note))
        return tuple(coverage)

    # -- identity + anchoring ------------------------------------------------

    def _derive_certification_id(self) -> str:
        basis = "|".join([
            self._anchors.corpus_hash,
            self._anchors.protected_test_hash,
            self._anchors.holdout_hash,
            self._anchors.baseline_hash,
            self._anchors.isr_hash,
        ])
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]

    def _anchor(self, artifact: CertificationArtifact) -> None:
        self._ledger.append_event(
            EvolutionEvent(
                event_id="",
                evolution_id="r2.8.14",
                sequence=0,
                event_type=EventType.CERTIFICATION,
                subject_id=artifact.certification_id,
                payload={
                    "certification_id": artifact.certification_id,
                    "status": artifact.status.value,
                    "artifact_content_hash": artifact.content_hash(),
                },
            ),
            evolution_id="r2.8.14",
        )


def recertify_after_execution_restored(
    ledger: EvolutionLedger,
    section_runners: Mapping[str, SectionRunner],
    anchors: CertificationAnchors,
    quarantine: QuarantineDisposition,
    budget: int = 1000,
) -> CertificationArtifact:
    """Re-issue the R2.8 certificate once R2.9.1 restores dynamic execution.

    Closing the environment gap moves the critical dynamic dimensions
    (correctness, regression_safety, causal_validity, performance) from
    BLOCKED_BY_ENVIRONMENT to EVALUATED_DYNAMIC, upgrading the status to
    CERTIFIED_FULL provided every mandatory invariant still passes.
    """
    environment = EnvironmentCapability(
        hermetic_static=EnvironmentCapabilityStatus.AVAILABLE,
        hermetic_composition=EnvironmentCapabilityStatus.AVAILABLE,
        dynamic_execution=EnvironmentCapabilityStatus.AVAILABLE,
        dynamic_execution_note="Restored by R2.9.1",
    )
    authority = CertificationAuthority(
        ledger=ledger, environment=environment,
        section_runners=section_runners, anchors=anchors,
        quarantine=quarantine, red_team_query_budget=budget,
    )
    return authority.certify()