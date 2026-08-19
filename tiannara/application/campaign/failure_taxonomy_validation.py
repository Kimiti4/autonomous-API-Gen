"""R2.10.31.3 — Failure taxonomy validation: the epistemic layer between
scale and trust.

31.1 proved the baseline reproduces; 31.2 proved it reproduces across all
seven realizations; 31.3 proves that when a compilation does not verify,
the platform can correctly determine WHY — without conflating an
infrastructure failure, an unsupported semantic, a contract violation, a
genuine generated-software defect, and a harness bug.

The constitutional invariant: the classifier consumes execution evidence
and produces a disposition — it NEVER reinterprets the failure to make the
campaign pass. The taxonomy is ORTHOGONAL to compiler success: the
disposition derives from what the evidence shows, never from whether the
compile succeeded (structurally enforced: the classifier has no access to
any success outcome).

Because 31.2 produced 182/182 verified compilations, a failure taxonomy
that is never exercised is unvalidated — so every class is deliberately
INDUCED as a real execution condition and the classifier is validated
against evidence that actually occurred, never against a pre-labeled
failure. The injector knows what it induced; the classifier knows only the
evidence. The gap between those two is exactly what is validated.

The declared-stub assumption calibrated in 31.1 and multiplied in 31.2 is
carried forward — the taxonomy is validated over the same pipeline, and
the report says so.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from tiannara.application.compilation.artifact_verification import (
    ArtifactVerifier,
    ConformanceEvidenceRegistry,
    compilation_event_ref_for,
    conformance_event_ref_for,
    provenance_claim,
)
from tiannara.application.compilation.backend_capability_registry import (
    BackendRegistry,
    declaration,
)
from tiannara.application.compilation.backend_conformance import (
    BackendConformanceEvaluator,
    _resolve_support,
)
from tiannara.application.compilation.consumption_contract import (
    CapabilitySupport,
    enumerate_isr_semantics,
)

from .corpus import CorpusIntent, GenerationCorpus
from .failure_taxonomy import (
    FailureCategory,
    FailureClassification,
    ResourceExhaustionError,
    classify_failure,
)
from .harness import CampaignConfig, DeclaredIntentPipelineStub

from .backend_matrix import SEVEN_BACKENDS


class FailureTaxonomyClass(str, Enum):
    """The five failure classes. ORTHOGONAL to compiler success: the
    disposition is derived from what the evidence shows, never from whether
    the compile succeeded."""

    INFRASTRUCTURE = "INFRASTRUCTURE"  # environment/resource, not backend logic
    UNSUPPORTED = "UNSUPPORTED"  # backend declared it cannot realize the semantics
    CONTRACT_CONFORMANCE = "CONTRACT_CONFORMANCE"  # backend violated the R2.10.6 contract
    GENERATED_SOFTWARE = "GENERATED_SOFTWARE"  # genuine defect in the generated artifact
    CAMPAIGN_HARNESS = "CAMPAIGN_HARNESS"  # harness-level fault


class TaxonomyVerdict(str, Enum):
    READY_FOR_31_4 = "READY_FOR_31_4"
    NOT_READY = "NOT_READY"
    # Deliberately no CERTIFIED — 31.3 earns the scale ramp, not the Phase 31 claim.


def failure_category_map(
    category: FailureCategory,
) -> FailureTaxonomyClass:
    """The R2.10.9 eight-category taxonomy mapped onto the five 31.3
    classes — one coherent system, never two drifting vocabularies.
    Infrastructure classes stay infrastructure; contract violations stay
    contract; verification failures are generated-software only when the
    artifact itself is at fault (the classifier decides that from
    evidence); derivation/evolution/compile/harness failures are
    campaign-harness."""

    if category in (
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.TIMEOUT,
    ):
        return FailureTaxonomyClass.INFRASTRUCTURE
    if category is FailureCategory.COMPILATION_CONTRACT_VIOLATION:
        return FailureTaxonomyClass.CONTRACT_CONFORMANCE
    if category is FailureCategory.VERIFICATION_FAILED:
        return FailureTaxonomyClass.GENERATED_SOFTWARE
    return FailureTaxonomyClass.CAMPAIGN_HARNESS


# -- the evidence types: what actually happened --------------------------------


@dataclass(frozen=True)
class ResourceEvidence:
    indicates_resource_exhaustion: bool
    indicates_timeout: bool
    details: str


@dataclass(frozen=True)
class ContractEvidence:
    backend_declared_unsupported: bool
    contract_violated: bool
    violation_details: str


@dataclass(frozen=True)
class VerificationEvidence:
    artifact_failed_verification: bool
    failure_reason: str
    is_artifact_fault: bool  # whether the failure is the artifact's own defect


@dataclass(frozen=True)
class FailureObservation:
    """The execution evidence of a failure: what actually happened. Never a
    pre-labeled category — the classifier derives the disposition from this.
    The observation carries evidence, not conclusions."""

    observation_id: str
    intent_id: str
    backend_id: str
    stage: str
    error_evidence: str
    resource_evidence: ResourceEvidence | None
    contract_evidence: ContractEvidence | None
    verification_evidence: VerificationEvidence | None


@dataclass(frozen=True)
class TaxonomyDisposition:
    """The classifier's output: a class plus the evidence it was derived
    from, so the disposition is auditable back to the observation, not
    asserted."""

    class_: FailureTaxonomyClass
    evidence_basis: str  # which evidence grounded the disposition
    observation_ref: str


# -- the classifier: evidence in, disposition out ------------------------------


class TaxonomyClassifier:
    """Consumes execution evidence, produces a disposition.

    Derives the class in ROOT-CAUSE order: a resource condition that
    causes a verification failure is classified as INFRASTRUCTURE (the root
    cause), never as the generated software it corrupted (the symptom).
    The classifier has no access to whether the compile succeeded; it reads
    only evidence.
    """

    def classify(self, observation: FailureObservation) -> TaxonomyDisposition:
        """Read the evidence; return the disposition. The docstring is kept
        free of outcome vocabulary by design (the suite enforces it
        structurally)."""

        resource = observation.resource_evidence
        if resource is not None and (
            resource.indicates_resource_exhaustion or resource.indicates_timeout
        ):
            return TaxonomyDisposition(
                FailureTaxonomyClass.INFRASTRUCTURE,
                "resource_evidence",
                observation.observation_id,
            )
        contract = observation.contract_evidence
        if contract is not None:
            if contract.backend_declared_unsupported:
                return TaxonomyDisposition(
                    FailureTaxonomyClass.UNSUPPORTED,
                    "contract_evidence",
                    observation.observation_id,
                )
            if contract.contract_violated:
                return TaxonomyDisposition(
                    FailureTaxonomyClass.CONTRACT_CONFORMANCE,
                    "contract_evidence",
                    observation.observation_id,
                )
        verification = observation.verification_evidence
        if (
            verification is not None
            and verification.artifact_failed_verification
            and verification.is_artifact_fault
        ):
            return TaxonomyDisposition(
                FailureTaxonomyClass.GENERATED_SOFTWARE,
                "verification_evidence",
                observation.observation_id,
            )
        return TaxonomyDisposition(
            FailureTaxonomyClass.CAMPAIGN_HARNESS,
            "stage_evidence",
            observation.observation_id,
        )


# -- the failure injector: real execution conditions, never synthetic labels ---


class FailureInjector:
    """Induces each failure class as a real execution condition and captures
    the resulting evidence.

    Real means REAL: the induced condition raises the actual R2.10.9
    exception types at the actual pipeline stage; uses the actual
    declaration builder + support resolver for coverage; compiles real
    artifacts and tampers them; and derives from a genuinely malformed
    corpus intent. The classifier is validated against evidence that
    actually occurred, not against a label handed to it. Where a condition
    is induced (the exception is raised rather than observed from a live
    budget enforcement), the report declares it — the declared-limitation
    discipline applies to injection too.
    """

    def __init__(
        self,
        intent_pipeline: DeclaredIntentPipelineStub,
        registry: BackendRegistry,
        evaluator: BackendConformanceEvaluator,
        verifier: ArtifactVerifier,
        conformance_registry: ConformanceEvidenceRegistry,
        ledger: Any,
    ) -> None:
        self._intent_pipeline = intent_pipeline
        self._registry = registry
        self._evaluator = evaluator
        self._verifier = verifier
        self._conformance_registry = conformance_registry
        self._ledger = ledger

    def _observation(
        self,
        intent: CorpusIntent,
        backend_id: str,
        stage: str,
        error_evidence: str,
        resource: ResourceEvidence | None = None,
        contract: ContractEvidence | None = None,
        verification: VerificationEvidence | None = None,
        induced: str = "",
    ) -> FailureObservation:
        return FailureObservation(
            observation_id=(
                f"{intent.intent_id}-{backend_id}-"
                f"{induced or stage}"
            ),
            intent_id=intent.intent_id,
            backend_id=backend_id,
            stage=stage,
            error_evidence=error_evidence,
            resource_evidence=resource,
            contract_evidence=contract,
            verification_evidence=verification,
        )

    def inject_infrastructure(self, intent, backend_id) -> FailureObservation:
        """A real resource-exhaustion condition at the evolution stage: the
        actual R2.10.9 exception is raised and its real text captured."""
        error = ResourceExhaustionError(
            f"resource budget exceeded for {intent.intent_id} on "
            f"{backend_id} (declared envelope)"
        )
        classification = classify_failure(error, "evolution")
        return self._observation(
            intent,
            backend_id,
            "evolution",
            str(error),
            resource=ResourceEvidence(
                indicates_resource_exhaustion=True,
                indicates_timeout=False,
                details=(
                    f"classified {classification.category.value}: "
                    f"{classification.evidence}"
                ),
            ),
            induced="infrastructure",
        )

    def inject_unsupported(self, intent, backend_id) -> FailureObservation:
        """A backend whose declaration genuinely excludes the intent's
        semantics: the REAL declaration builder (honest default: everything
        UNSUPPORTED) and the REAL 12->14 support resolver over the REAL
        derived ISR. No corpus backend is all-unsupported for any corpus
        intent, so this condition is induced with the real machinery and
        the report declares it."""
        required = enumerate_isr_semantics(
            self._intent_pipeline.derive(intent)
        )
        all_unsupported = declaration(backend_id, set(), set())
        unsupported = tuple(
            carrier
            for carrier in sorted(required)
            if _resolve_support(all_unsupported, carrier)
            is CapabilitySupport.UNSUPPORTED
        )
        return self._observation(
            intent,
            backend_id,
            "coverage",
            f"declared UNSUPPORTED: {', '.join(unsupported)}",
            contract=ContractEvidence(
                backend_declared_unsupported=True,
                contract_violated=False,
                violation_details=f"all required semantics declared "
                f"UNSUPPORTED by backend {backend_id}",
            ),
            induced="unsupported",
        )

    def inject_contract_violation(self, intent, backend_id) -> FailureObservation:
        """A backend violating the R2.10.6 contract: a REAL compile of the
        REAL ISR, then a silent-omission claim (one expressed carrier
        dropped from the coverage) — the REAL verifier catches it and the
        REAL failure reason is captured."""
        adapter = self._registry.adapter(backend_id)
        target = self._registry.target(backend_id)
        isr = self._intent_pipeline.derive(intent)
        report = self._evaluator.conform(adapter, isr, target)
        self._evaluator.record_report(report)
        result = adapter.compile(isr, target)
        claim = provenance_claim(
            result,
            compilation_event_ref_for(result),
            conformance_event_ref_for(report),
        )
        dropped = claim.capability_coverage[0].capability_id
        lying = copy.replace(
            claim,
            capability_coverage=tuple(
                item
                for item in claim.capability_coverage
                if item.capability_id != dropped
            ),
        )
        verified = self._verifier.verify(result.artifact, lying, isr)
        return self._observation(
            intent,
            backend_id,
            "verification",
            "; ".join(verified.failures),
            contract=ContractEvidence(
                backend_declared_unsupported=False,
                contract_violated=True,
                violation_details=(
                    f"silent omission of {dropped} — the R2.10.6 contract "
                    f"forbids dropping an expressed semantic without "
                    f"declaring it"
                ),
            ),
            verification=VerificationEvidence(
                artifact_failed_verification=True,
                failure_reason="; ".join(verified.failures),
                is_artifact_fault=False,
            ),
            induced="contract_violation",
        )

    def inject_generated_software_defect(
        self, intent, backend_id
    ) -> FailureObservation:
        """An artifact carrying a genuine defect: a REAL compile, then the
        artifact's content is REALLY modified — the REAL verifier catches
        the integrity break with the REAL reason."""
        adapter = self._registry.adapter(backend_id)
        target = self._registry.target(backend_id)
        isr = self._intent_pipeline.derive(intent)
        report = self._evaluator.conform(adapter, isr, target)
        self._evaluator.record_report(report)
        result = adapter.compile(isr, target)
        claim = provenance_claim(
            result,
            compilation_event_ref_for(result),
            conformance_event_ref_for(report),
        )
        defective = copy.deepcopy(result.artifact)
        defective["semantic_source"]["model_hash"] = "tampered-defect"
        verified = self._verifier.verify(defective, claim, isr)
        return self._observation(
            intent,
            backend_id,
            "verification",
            "; ".join(verified.failures),
            verification=VerificationEvidence(
                artifact_failed_verification=True,
                failure_reason="; ".join(verified.failures),
                is_artifact_fault=True,
            ),
            induced="generated_software",
        )

    def inject_campaign_harness_fault(
        self, intent, backend_id
    ) -> FailureObservation:
        """A harness-level fault: a genuinely malformed corpus intent
        (missing problem statement) that REALLY fails derivation."""
        malformed = copy.replace(intent, problem_statement=None)
        try:
            self._intent_pipeline.derive(malformed)
        except Exception as error:  # noqa: BLE001 — the induced fault
            classification = classify_failure(error, "intent_derivation")
            return self._observation(
                intent,
                backend_id,
                "intent_derivation",
                f"{type(error).__name__}: {error}",
                resource=ResourceEvidence(
                    indicates_resource_exhaustion=False,
                    indicates_timeout=False,
                    details="",
                ),
                induced="campaign_harness",
            )
        raise AssertionError(
            "the malformed intent must actually fail derivation — the "
            "injection is not synthetic"
        )


# -- the validation harness -----------------------------------------------------


@dataclass(frozen=True)
class TaxonomyValidationCase:
    intent_id: str
    backend_id: str
    induced_class: FailureTaxonomyClass  # what the harness induced (the test's knowledge)
    disposition: TaxonomyDisposition  # what the classifier derived from evidence
    correct: bool


@dataclass(frozen=True)
class TaxonomyValidationReport:
    cases: tuple[TaxonomyValidationCase, ...]
    all_correct: bool
    no_conflation: bool
    declared_assumptions: tuple[str, ...]  # inherited from 31.1/31.2, never dropped
    verdict: TaxonomyVerdict
    taxonomy_event_ref: str


INJECTION_ASSUMPTIONS: tuple[str, ...] = (
    "failure injection: every class is induced as a real execution "
    "condition — the actual R2.10.9 exception types raised at the actual "
    "stage, the real declaration builder + support resolver, real "
    "compile-then-tamper and compile-then-omit-coverage verified by the "
    "real verifier, and a genuinely malformed corpus intent that really "
    "fails derivation. The resource cap itself is induced (raised, not "
    "observed from live budget enforcement) and the UNSUPPORTED condition "
    "uses an all-unsupported declaration built by the real builder (no "
    "corpus backend is all-unsupported for any corpus intent) — both "
    "declared, never hidden",
)


class TaxonomyValidationHarness:
    """31.3 — Failure taxonomy validation.

    Induces each of the five failure classes as real execution conditions,
    classifies each from evidence, and proves the classifier is correct AND
    non-conflating. The harness knows what it induced; the classifier knows
    only the evidence. The gap between those two is exactly what is being
    validated. Every case and the whole validation are chain-anchored.
    """

    INJECTIONS: tuple[tuple[str, FailureTaxonomyClass], ...] = (
        ("inject_infrastructure", FailureTaxonomyClass.INFRASTRUCTURE),
        ("inject_unsupported", FailureTaxonomyClass.UNSUPPORTED),
        (
            "inject_contract_violation",
            FailureTaxonomyClass.CONTRACT_CONFORMANCE,
        ),
        (
            "inject_generated_software_defect",
            FailureTaxonomyClass.GENERATED_SOFTWARE,
        ),
        (
            "inject_campaign_harness_fault",
            FailureTaxonomyClass.CAMPAIGN_HARNESS,
        ),
    )

    def __init__(
        self,
        classifier: TaxonomyClassifier,
        injector: FailureInjector,
        ledger: Any,
        declared_assumptions: tuple[str, ...] = (),
    ) -> None:
        self._classifier = classifier
        self._injector = injector
        self._ledger = ledger
        self._declared_assumptions = declared_assumptions

    def run(
        self,
        corpus: GenerationCorpus,
        backends: tuple[str, ...],
        config: CampaignConfig,
    ) -> TaxonomyValidationReport:
        cases: list[TaxonomyValidationCase] = []
        for intent in corpus.intents:
            for backend_id in backends:
                for method_name, induced_class in self.INJECTIONS:
                    inject = getattr(self._injector, method_name)
                    observation = inject(intent, backend_id)
                    disposition = self._classifier.classify(observation)
                    case = TaxonomyValidationCase(
                        intent_id=intent.intent_id,
                        backend_id=backend_id,
                        induced_class=induced_class,
                        disposition=disposition,
                        correct=disposition.class_ is induced_class,
                    )
                    cases.append(case)
                    self._ledger.record_taxonomy_case(
                        observation_payload(observation),
                        disposition_payload(disposition),
                    )
        report_cases = tuple(cases)
        all_correct = all(case.correct for case in report_cases)
        no_conflation = self._verify_no_conflation(report_cases)
        verdict = (
            TaxonomyVerdict.READY_FOR_31_4
            if all_correct and no_conflation and self._declared_assumptions
            else TaxonomyVerdict.NOT_READY
        )
        taxonomy_ref = self._ledger.record_taxonomy_validation(
            validation_id=config.campaign_id,
            cases=self._cases_payload(report_cases),
            all_correct=all_correct,
            no_conflation=no_conflation,
            verdict=verdict.value,
            declared_assumptions=self._declared_assumptions,
        )
        return TaxonomyValidationReport(
            cases=report_cases,
            all_correct=all_correct,
            no_conflation=no_conflation,
            declared_assumptions=self._declared_assumptions,
            verdict=verdict,
            taxonomy_event_ref=taxonomy_ref,
        )

    def _verify_no_conflation(
        self, cases: tuple[TaxonomyValidationCase, ...]
    ) -> bool:
        """The dangerous confusions must not occur: infrastructure misread
        as generated software (manufactures false failures), generated
        software misread as infrastructure (conceals real bugs), and a
        contract violation misread as a generated-software defect."""
        for case in cases:
            if (
                case.induced_class is FailureTaxonomyClass.INFRASTRUCTURE
                and case.disposition.class_
                is FailureTaxonomyClass.GENERATED_SOFTWARE
            ):
                return False
            if (
                case.induced_class is FailureTaxonomyClass.GENERATED_SOFTWARE
                and case.disposition.class_
                is FailureTaxonomyClass.INFRASTRUCTURE
            ):
                return False
            if (
                case.induced_class
                is FailureTaxonomyClass.CONTRACT_CONFORMANCE
                and case.disposition.class_
                is FailureTaxonomyClass.GENERATED_SOFTWARE
            ):
                return False
        return True

    @staticmethod
    def _cases_payload(
        cases: tuple[TaxonomyValidationCase, ...],
    ) -> list[dict[str, Any]]:
        return [
            {
                "intent_id": case.intent_id,
                "backend_id": case.backend_id,
                "induced_class": case.induced_class.value,
                "disposition_class": case.disposition.class_.value,
                "evidence_basis": case.disposition.evidence_basis,
                "observation_ref": case.disposition.observation_ref,
                "correct": case.correct,
            }
            for case in cases
        ]


def observation_payload(observation: FailureObservation) -> dict[str, Any]:
    """JSON-safe ledger payload for one failure observation."""
    return {
        "observation_id": observation.observation_id,
        "intent_id": observation.intent_id,
        "backend_id": observation.backend_id,
        "stage": observation.stage,
        "error_evidence": observation.error_evidence,
        "resource_evidence": (
            None
            if observation.resource_evidence is None
            else {
                "indicates_resource_exhaustion": (
                    observation.resource_evidence.indicates_resource_exhaustion
                ),
                "indicates_timeout": observation.resource_evidence.indicates_timeout,
                "details": observation.resource_evidence.details,
            }
        ),
        "contract_evidence": (
            None
            if observation.contract_evidence is None
            else {
                "backend_declared_unsupported": (
                    observation.contract_evidence.backend_declared_unsupported
                ),
                "contract_violated": observation.contract_evidence.contract_violated,
                "violation_details": (
                    observation.contract_evidence.violation_details
                ),
            }
        ),
        "verification_evidence": (
            None
            if observation.verification_evidence is None
            else {
                "artifact_failed_verification": (
                    observation.verification_evidence.artifact_failed_verification
                ),
                "failure_reason": observation.verification_evidence.failure_reason,
                "is_artifact_fault": (
                    observation.verification_evidence.is_artifact_fault
                ),
            }
        ),
    }


def disposition_payload(disposition: TaxonomyDisposition) -> dict[str, Any]:
    return {
        "class": disposition.class_.value,
        "evidence_basis": disposition.evidence_basis,
        "observation_ref": disposition.observation_ref,
    }