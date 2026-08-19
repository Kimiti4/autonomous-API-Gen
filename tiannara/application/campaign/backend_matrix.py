"""R2.10.31.2 — the backend matrix experiment: coverage and invariance at
matrix scale, not throughput.

For each of the 26 calibrated intents, the ISR is derived ONCE and compiled
through all seven real backends, so the comparison is over one semantic
source realized many ways. Every (intent, backend) case is disposed into
exactly one of the five disposition classes; the matrix measures coverage
and invariance, never raw success rate.

EXPLICITLY_UNSUPPORTED is a LEGITIMATE terminal disposition — legitimate
because R2.10.7 made silent omission structurally impossible: the backend's
declared coverage is checked BEFORE compiling (``adapter.coverage_for``),
and a case whose required semantics are ALL declared UNSUPPORTED is
disposed honestly instead of being compiled into a doomed artifact. The
only truly fatal outcome is a case with no disposition at all, because
that's the one that can't be audited.

The declared-stub assumption calibrated in 31.1 is MECHANICALLY carried
into the matrix report and its ledger event (never re-derived, never
dropped): 31.2 measures the same pipeline 31.1 calibrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from constitutional_architecture.isr.model import ISR
from tiannara.application.compilation.artifact_verification import (
    ArtifactVerifier,
    ConformanceEvidenceRegistry,
    compilation_event_ref_for,
    conformance_event_ref_for,
    provenance_claim,
)
from tiannara.application.compilation.backend_conformance import (
    BackendConformanceEvaluator,
)
from tiannara.application.compilation.backend_capability_registry import (
    BackendRegistry,
)
from tiannara.application.compilation.consumption_contract import (
    CapabilityCoverage,
    CapabilitySupport,
    enumerate_isr_semantics,
)

from .corpus import CorpusIntent, GenerationCorpus
from .failure_taxonomy import (
    FailureCategory,
    FailureClassification,
    classify_failure,
)
from .harness import CampaignConfig

SEVEN_BACKENDS: tuple[str, ...] = (
    "react",
    "fastapi",
    "postgres",
    "terraform",
    "cicd",
    "pytest",
    "markdown",
)


class MatrixDisposition(str, Enum):
    """The disposition of one (intent, backend) case."""

    VERIFIED_COMPILATION = "VERIFIED_COMPILATION"  # compiled AND independently verified
    SUCCESSFUL_COMPILATION = "SUCCESSFUL_COMPILATION"  # compiled; verification ran, did not verify
    EXPLICITLY_UNSUPPORTED = "EXPLICITLY_UNSUPPORTED"  # backend declared UNSUPPORTED for this intent's semantics
    DIAGNOSED_FAILURE = "DIAGNOSED_FAILURE"  # attempted and failed, classified by the R2.10.9 taxonomy
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"  # environment/resource failure, not backend logic


class MatrixVerdict(str, Enum):
    READY_FOR_31_3 = "READY_FOR_31_3"
    NOT_READY = "NOT_READY"
    # Deliberately no CERTIFIED — 31.2 earns 31.3, not the Phase 31 claim.


@dataclass(frozen=True)
class MatrixCase:
    """One cell of the 26 x 7 matrix."""

    intent_id: str
    backend_id: str
    disposition: MatrixDisposition
    isr_hash: str | None  # the semantic source (shared per intent)
    artifact_hash: str | None  # the realization (diverges per backend)
    verification_verified: bool | None
    unsupported_semantics: tuple[str, ...]  # named, never silent
    failure_classification: FailureClassification | None
    conformance_evidence_ref: str  # the R2.10.7 conformance report on the chain
    provenance_chain_ref: str | None  # the case's terminal chain anchor


@dataclass(frozen=True)
class BackendMatrixSummary:
    """Per-backend rollup: how this backend disposed across the 26 intents."""

    backend_id: str
    verified: int
    successful: int
    explicitly_unsupported: int
    diagnosed_failure: int
    infrastructure_failure: int


@dataclass(frozen=True)
class MatrixReport:
    """The durable artifact of 31.2 — coverage and invariance, not
    throughput."""

    matrix_id: str
    cases: tuple[MatrixCase, ...]
    per_backend_summary: Mapping[str, BackendMatrixSummary]
    cross_backend_invariance_held: bool
    declared_assumptions: tuple[str, ...]  # inherited from 31.1, never dropped
    verdict: MatrixVerdict
    matrix_event_ref: str


def unsupported_required(
    required: frozenset[str], coverage: tuple[CapabilityCoverage, ...]
) -> tuple[str, ...]:
    """The required semantics this backend declares UNSUPPORTED — named,
    never silent. The EXPLICITLY_UNSUPPORTED decision is made BEFORE
    compiling, from the backend's declared coverage."""
    declared_unsupported = frozenset(
        item.capability_id
        for item in coverage
        if item.support is CapabilitySupport.UNSUPPORTED
    )
    return tuple(sorted(required & declared_unsupported))


def _infrastructure_classified(
    classification: FailureClassification,
) -> bool:
    """INFRASTRUCTURE_FAILURE is environment/resource — a retry could
    plausibly succeed (recoverable). Everything else that failed is a
    DIAGNOSED_FAILURE: backend logic, contracts, or verification."""
    return classification.category in (
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.TIMEOUT,
    )


def case_payload(case: MatrixCase) -> dict[str, Any]:
    """JSON-safe ledger payload for one matrix case."""
    return {
        "intent_id": case.intent_id,
        "backend_id": case.backend_id,
        "disposition": case.disposition.value,
        "isr_hash": case.isr_hash,
        "artifact_hash": case.artifact_hash,
        "verification_verified": case.verification_verified,
        "unsupported_semantics": list(case.unsupported_semantics),
        "failure_classification": (
            case.failure_classification.category.value
            if case.failure_classification
            else None
        ),
        "conformance_evidence_ref": case.conformance_evidence_ref,
        "provenance_chain_ref": case.provenance_chain_ref,
    }


def cases_payload(cases: tuple[MatrixCase, ...]) -> list[dict[str, Any]]:
    return [case_payload(case) for case in cases]


class MatrixHarness:
    """31.2 — Backend matrix experiment.

    For each intent, derives the ISR ONCE and compiles it through all seven
    backends, so the comparison is over one semantic source realized many
    ways. Each case is disposed into one of the five classes; the matrix
    measures coverage and invariance, never raw throughput. The frozen
    R2.10.6-8 seams are invoked as black boxes (conform -> record ->
    compile -> claim -> verify); the harness itself never reaches into the
    ISR or the verifier.
    """

    def __init__(
        self,
        intent_pipeline: Any,
        registry: BackendRegistry,
        evaluator: BackendConformanceEvaluator,
        verifier: ArtifactVerifier,
        conformance_registry: ConformanceEvidenceRegistry,
        ledger: Any,
        declared_assumptions: tuple[str, ...] = (),
    ) -> None:
        self._intent_pipeline = intent_pipeline
        self._registry = registry
        self._evaluator = evaluator
        self._verifier = verifier
        self._conformance_registry = conformance_registry
        self._ledger = ledger
        self._declared_assumptions = declared_assumptions

    def run(
        self, corpus: GenerationCorpus, config: CampaignConfig
    ) -> MatrixReport:
        cases: list[MatrixCase] = []
        for intent in corpus.intents:
            # One ISR per intent, shared across all seven backends — the
            # cross-backend comparison is genuinely over one semantic source.
            isr = self._intent_pipeline.derive(intent)
            for backend_id in SEVEN_BACKENDS:
                cases.append(self._run_case(intent, isr, backend_id))
        report_cases = tuple(cases)
        invariance = self._verify_cross_backend_invariance(report_cases)
        verdict = self._render_verdict(report_cases, invariance)
        matrix_ref = self._ledger.record_matrix(
            matrix_id=config.campaign_id,
            cases=cases_payload(report_cases),
            invariance=invariance,
            verdict=verdict.value,
            declared_assumptions=self._declared_assumptions,
        )
        return MatrixReport(
            matrix_id=config.campaign_id,
            cases=report_cases,
            per_backend_summary=self._summarize_per_backend(report_cases),
            cross_backend_invariance_held=invariance,
            declared_assumptions=self._declared_assumptions,
            verdict=verdict,
            matrix_event_ref=matrix_ref,
        )

    def _run_case(
        self, intent: CorpusIntent, isr: ISR, backend_id: str
    ) -> MatrixCase:
        adapter = self._registry.adapter(backend_id)
        target = self._registry.target(backend_id)
        required = enumerate_isr_semantics(isr)
        coverage = adapter.coverage_for(isr)
        unsupported = unsupported_required(required, coverage)

        report = self._evaluator.conform(adapter, isr, target)
        self._evaluator.record_report(report)
        evidence_ref = conformance_event_ref_for(report)

        # The declared coverage decides BEFORE compiling: a case whose
        # required semantics are ALL declared UNSUPPORTED is disposed
        # honestly, never compiled into a doomed artifact.
        if required <= frozenset(unsupported):
            return MatrixCase(
                intent_id=intent.intent_id,
                backend_id=backend_id,
                disposition=MatrixDisposition.EXPLICITLY_UNSUPPORTED,
                isr_hash=report.isr_semantic_hash_at_conformance,
                artifact_hash=None,
                verification_verified=None,
                unsupported_semantics=unsupported,
                failure_classification=None,
                conformance_evidence_ref=evidence_ref,
                provenance_chain_ref=evidence_ref,
            )
        try:
            result = adapter.compile(isr, target)
            claim = provenance_claim(
                result,
                compilation_event_ref_for(result),
                evidence_ref,
            )
            verified = self._verifier.verify(result.artifact, claim, isr)
            disposition = (
                MatrixDisposition.VERIFIED_COMPILATION
                if verified.verified
                else MatrixDisposition.SUCCESSFUL_COMPILATION
            )
            return MatrixCase(
                intent_id=intent.intent_id,
                backend_id=backend_id,
                disposition=disposition,
                isr_hash=result.isr_hash,
                artifact_hash=result.artifact_hash,
                verification_verified=verified.verified,
                unsupported_semantics=unsupported,
                failure_classification=None,
                conformance_evidence_ref=evidence_ref,
                provenance_chain_ref=verified.verification_event_ref,
            )
        except Exception as error:  # noqa: BLE001 — matrix boundary
            classification = classify_failure(error, "matrix")
            disposition = (
                MatrixDisposition.INFRASTRUCTURE_FAILURE
                if _infrastructure_classified(classification)
                else MatrixDisposition.DIAGNOSED_FAILURE
            )
            return MatrixCase(
                intent_id=intent.intent_id,
                backend_id=backend_id,
                disposition=disposition,
                isr_hash=report.isr_semantic_hash_at_conformance,
                artifact_hash=None,
                verification_verified=None,
                unsupported_semantics=unsupported,
                failure_classification=classification,
                conformance_evidence_ref=evidence_ref,
                provenance_chain_ref=None,
            )

    def _verify_cross_backend_invariance(
        self, cases: tuple[MatrixCase, ...]
    ) -> bool:
        """For each intent, every backend that compiled it must bind to ONE
        semantic source. Artifacts are REQUIRED to differ structurally;
        their source is REQUIRED to agree. A disagreement is an invariance
        violation regardless of how many cases succeeded."""
        by_intent: dict[str, set[str]] = {}
        for case in cases:
            if (
                case.artifact_hash is not None
                and case.isr_hash is not None
                and case.disposition
                in (
                    MatrixDisposition.VERIFIED_COMPILATION,
                    MatrixDisposition.SUCCESSFUL_COMPILATION,
                )
            ):
                by_intent.setdefault(case.intent_id, set()).add(case.isr_hash)
        return all(
            len(sources) == 1 for sources in by_intent.values()
        )

    def _summarize_per_backend(
        self, cases: tuple[MatrixCase, ...]
    ) -> Mapping[str, BackendMatrixSummary]:
        summaries: dict[str, BackendMatrixSummary] = {}
        for backend_id in SEVEN_BACKENDS:
            backend_cases = [
                case for case in cases if case.backend_id == backend_id
            ]
            summaries[backend_id] = BackendMatrixSummary(
                backend_id=backend_id,
                verified=sum(
                    1
                    for case in backend_cases
                    if case.disposition
                    is MatrixDisposition.VERIFIED_COMPILATION
                ),
                successful=sum(
                    1
                    for case in backend_cases
                    if case.disposition
                    is MatrixDisposition.SUCCESSFUL_COMPILATION
                ),
                explicitly_unsupported=sum(
                    1
                    for case in backend_cases
                    if case.disposition
                    is MatrixDisposition.EXPLICITLY_UNSUPPORTED
                ),
                diagnosed_failure=sum(
                    1
                    for case in backend_cases
                    if case.disposition
                    is MatrixDisposition.DIAGNOSED_FAILURE
                ),
                infrastructure_failure=sum(
                    1
                    for case in backend_cases
                    if case.disposition
                    is MatrixDisposition.INFRASTRUCTURE_FAILURE
                ),
            )
        return summaries

    def _render_verdict(
        self, cases: tuple[MatrixCase, ...], invariance: bool
    ) -> MatrixVerdict:
        all_disposed = all(case.disposition is not None for case in cases)
        non_verified_classified = all(
            case.disposition
            in (
                MatrixDisposition.SUCCESSFUL_COMPILATION,
                MatrixDisposition.EXPLICITLY_UNSUPPORTED,
                MatrixDisposition.DIAGNOSED_FAILURE,
                MatrixDisposition.INFRASTRUCTURE_FAILURE,
            )
            for case in cases
            if case.disposition is not MatrixDisposition.VERIFIED_COMPILATION
        )
        # The 31.1 declared-stub assumption must propagate — never dropped.
        assumptions_inherited = bool(self._declared_assumptions)
        return (
            MatrixVerdict.READY_FOR_31_3
            if (
                all_disposed
                and non_verified_classified
                and invariance
                and assumptions_inherited
            )
            else MatrixVerdict.NOT_READY
        )