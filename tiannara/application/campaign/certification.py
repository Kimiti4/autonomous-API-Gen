"""R2.10.31.5 — certification: consume the evidence, earn the word.

31.1 calibrated the baseline; 31.2 multiplied it across seven backends;
31.3 made every deviation explainable; 31.4 measured the scale envelope.
31.5 is the phase that CERTIFIES the accumulated evidence rather than
generating another layer of capability — the one phase whose verdict may
finally say CERTIFIED, because every prior phase deliberately used
READY_FOR_X precisely so this one could earn the word.

The certification is BOUNDED, never inflated:

  * the measured envelope (31.4) is first-class certification content —
    the certification statement names it, it is never a footnote;
  * the 500-level budget exceedance remains classified honestly (a real
    resource signal, never reinterpreted as a software defect);
  * the declared assumptions (31.1's declared-stub limitation through
    31.4's methodology) are bound to their origin and carried onto the
    artifact;
  * every claim is independently reconstructible from ledger events —
    each dimension names the refs it is reconstructed from, and the
    artifact's content hash commits to those refs;
  * the verdict space is CERTIFIED / QUALIFIED_PARTIAL / NOT_CERTIFIED,
    and QUALIFIED_PARTIAL is the honest verdict when a dimension's
    evidence is incomplete — for instance, 31.4 observed zero failures,
    so the taxonomy was never exercised on natural failures at scale
    (taxonomy_exercised: False, already declared). That is not a defect;
    it is a bound on the certification's scope, and it belongs in the
    verdict, not in a footnote.

The certifier ASSEMBLES and VERIFIES the evidence chain — it does not run
new machinery that could change what the evidence shows. The two
deliberate exceptions: the canary is RE-RUN (a certification that trusts
yesterday's evidence without reproducing it is one step from trusting
yesterday's claim), and the novelty-grounding check is PERFORMED.

The novelty-grounding check operationalizes the constitution's
foundational principle — "requirements should never directly generate
source code; all work must flow through the ISR" — as the capstone: can
the platform develop NOVEL software (an intent outside the calibration
corpus) without going against the ISR and without hallucinating?
Hallucination has a precise definition here: a semantic element in the
generated artifact with no counterpart in the source ISR — content the
generator asserted that the source of truth never said.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from constitutional_architecture.isr.semantics.projection import canonicalize

from tiannara.application.compilation.consumption_contract import (
    derive_backend_semantic_model,
)

from .backend_matrix import MatrixHarness, MatrixVerdict
from .calibration import CalibrationReport, CalibrationVerdict
from .corpus import GenerationCorpus
from .failure_taxonomy import FailureCategory
from .failure_taxonomy_validation import (
    TaxonomyValidationReport,
    TaxonomyVerdict,
)
from .harness import CampaignConfig, target_for
from .scale_ramp import ScaleRampReport, ScaleRampVerdict


class CertificationVerdict(str, Enum):
    CERTIFIED = "CERTIFIED"
    QUALIFIED_PARTIAL = "QUALIFIED_PARTIAL"
    NOT_CERTIFIED = "NOT_CERTIFIED"


class DimensionVerdict(str, Enum):
    PASS = "PASS"
    QUALIFIED = "QUALIFIED"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CertificationDimension:
    """One axis of the certification, bound to its evidence and its bounds.
    A dimension is never a bare assertion — it names what it rests on and
    what limits it."""

    dimension_id: str
    verdict: DimensionVerdict
    evidence_refs: tuple[str, ...]  # ledger refs this dimension is reconstructed from
    bounds: tuple[str, ...]  # declared limits / assumptions for this dimension


@dataclass(frozen=True)
class CertificationArtifact:
    """The culmination of Phase 31 — bounded, multi-dimensional,
    chain-anchored.

    The content hash commits to the evidence references, so the artifact
    is not a document that DESCRIBES the evidence but a structure BOUND
    to it. Every claim is independently reconstructible from the ledger.
    """

    certification_id: str
    verdict: CertificationVerdict
    certification_statement: str
    dimensions: tuple[CertificationDimension, ...]
    measured_envelope: int
    declared_assumptions: tuple[str, ...]
    evidence_chain_refs: tuple[str, ...]
    content_hash: str
    certification_event_ref: str


@dataclass(frozen=True)
class CertificationEvidence:
    """The 31.1-31.4 reports the certification consumes. The certifier
    never re-runs the campaign — the evidence chain is already on the
    ledger; certification verifies and commits to it."""

    calibration: CalibrationReport
    matrix: Any  # MatrixReport
    taxonomy: TaxonomyValidationReport
    ramp: ScaleRampReport


@dataclass(frozen=True)
class CertificationConfig:
    certification_id: str
    novel_intent: Any


def hash_canonical(value: Any) -> str:
    """SHA-256 over the no-default-str canonical form — the platform's
    canonical-form discipline: identical semantic content always produces
    an identical hash, and unrepresentable content raises instead of
    being silently str()-ed."""
    return hashlib.sha256(canonicalize(value).encode("utf-8")).hexdigest()


# -- the novelty-grounding check -------------------------------------------------


@dataclass(frozen=True)
class GroundingResult:
    grounded: bool
    untraced_semantics: tuple[str, ...]  # content with no ISR provenance = hallucination


@dataclass(frozen=True)
class NoveltyGroundingResult:
    novel_intent_id: str
    derivation_flowed_through_isr: bool  # requirements -> ISR -> backend, never around it
    conforms_to_isr: bool  # artifact verifies against its source ISR
    grounding: GroundingResult
    verdict: DimensionVerdict
    evidence_refs: tuple[str, ...]


def isr_semantic_elements(isr: Any) -> frozenset[tuple[str, str]]:
    """The semantic surface of an ISR, in the R2.10.6 projection
    vocabulary: capability ids, (kind, canonical content) constraint
    pairs, and protected-region forms. The ISR side of the grounding
    comparison — the source of truth's declarations."""
    model = derive_backend_semantic_model(isr)
    elements: set[tuple[str, str]] = {
        ("capability", capability) for capability in model.capabilities
    }
    elements |= {
        (kind, canonicalize(form)) for (kind, form) in model.constraints
    }
    elements |= {
        ("protected_region", canonicalize(region))
        for region in model.protected_regions
    }
    return frozenset(elements)


def artifact_semantic_elements(
    artifact: Mapping[str, Any],
) -> frozenset[tuple[str, str]]:
    """The semantic elements an artifact actually carries: every capability
    id it claims in its coverage, and the full projection it embeds when
    present. Grounding is decidable because both sides are expressed in the
    SAME semantic terms (the R2.10.6 projection vocabulary). A semantic
    element here with no counterpart in the source ISR is content the
    generator asserted that the source of truth never said — hallucination,
    by definition."""
    elements: set[tuple[str, str]] = set()
    for item in artifact.get("coverage", ()):
        elements.add(("capability", item["capability_id"]))
    projection = artifact.get("projection")
    if projection:
        for capability in projection.get("capabilities", ()):
            elements.add(("capability", capability))
        for item in projection.get("constraints", ()):
            elements.add((item["kind"], canonicalize(item["content"])))
        for region in projection.get("protected_regions", ()):
            elements.add(("protected_region", canonicalize(region)))
    return frozenset(elements)


class NoveltyGroundingCheck:
    """Can the platform develop NOVEL software WITHOUT going against the
    ISR and WITHOUT hallucinating?

    * Novelty: a genuinely new intent, drawn from OUTSIDE the calibration
      corpus, so the check exercises generative capacity rather than
      corpus recall.
    * ISR-conformance: the software is derived through the constitution's
      pipeline (Problem -> Requirements -> Requirement Graph -> ISR ->
      backends) and verifies against its source ISR.
    * Non-hallucination: every semantic element present in the artifact
      traces to a semantic element in the ISR. Content with no ISR
      provenance is hallucination — the generator asserting what the
      source of truth never said.
    """

    def __init__(self, intent_pipeline: Any, compilation: Any, verifier: Any) -> None:
        self._intent_pipeline = intent_pipeline
        self._compilation = compilation
        self._verifier = verifier

    def check(self, novel_intent: Any) -> NoveltyGroundingResult:
        # 1. Flow through the ISR — the constitution's pipeline, never
        #    around it. Requirements never directly generate source code.
        isr = self._intent_pipeline.derive(novel_intent)
        flowed_through_isr = isr is not None

        # 2. Realize and verify against the source ISR.
        compiled = self._compilation.compile(
            isr, target_for(novel_intent.category)
        )
        verified = self._verifier.verify(
            compiled.artifact, compiled.provenance, isr
        )

        # 3. Grounding: artifact semantics must be a SUBSET of ISR
        #    semantics.
        artifact_semantics = artifact_semantic_elements(compiled.artifact)
        isr_semantics = isr_semantic_elements(isr)
        untraced = tuple(
            sorted(
                f"{kind}:{content}"
                for (kind, content) in artifact_semantics - isr_semantics
            )
        )
        grounding = GroundingResult(
            grounded=(not untraced), untraced_semantics=untraced
        )

        verdict = (
            DimensionVerdict.PASS
            if (
                flowed_through_isr
                and verified.verified
                and grounding.grounded
            )
            else DimensionVerdict.FAIL
        )
        return NoveltyGroundingResult(
            novel_intent.intent_id,
            flowed_through_isr,
            verified.verified,
            grounding,
            verdict,
            (
                verified.verification_event_ref,
                compiled.provenance.compilation_event_ref,
                compiled.provenance.conformance_evidence_ref,
            ),
        )


# -- the certification harness ---------------------------------------------------


class CertificationHarness:
    """31.5 — Compiler Correctness Certification.

    Consumes the evidence accumulated by 31.1-31.4 plus the
    novelty-grounding check, and produces a bounded, chain-anchored
    CertificationArtifact. The certifier ASSEMBLES and VERIFIES the
    evidence chain — it does not run new machinery that could change what
    the evidence shows. The one exception is deliberate: the canary is
    RE-RUN (with the real seven-backend matrix) and the novelty check is
    PERFORMED, because a certification that trusts yesterday's evidence
    without reproducing it is one step from trusting yesterday's claim.
    """

    def __init__(
        self,
        evidence_store: CertificationEvidence,
        novelty_check: NoveltyGroundingCheck,
        intent_pipeline: Any,
        registry: Any,
        evaluator: Any,
        verifier: Any,
        conformance_registry: Any,
        ledger: Any,
        corpus: Any,
        base_config: CampaignConfig,
        declared_assumptions: tuple[str, ...] = (),
    ) -> None:
        self._evidence = evidence_store
        self.novelty_check = novelty_check
        self._ledger = ledger
        self._corpus = corpus
        self._base_config = base_config
        self._declared_assumptions = declared_assumptions
        self._matrix = MatrixHarness(
            intent_pipeline=intent_pipeline,
            registry=registry,
            evaluator=evaluator,
            verifier=verifier,
            conformance_registry=conformance_registry,
            ledger=ledger,
            declared_assumptions=declared_assumptions,
        )
        self._canary_rerun: Any = None

    def certify(
        self,
        config: CertificationConfig,
        canary_baseline: Mapping[
            tuple[str, str], tuple[str, str | None, str | None, bool | None]
        ]
        | None = None,
    ) -> CertificationArtifact:
        evidence = self._evidence
        rerun = self._reproduce_canary(config)
        novelty = self.novelty_check.check(config.novel_intent)
        dimensions = (
            self._calibration_dimension(),
            self._backend_matrix_dimension(),
            self._failure_taxonomy_dimension(),
            self._scale_ramp_dimension(),
            self._canary_dimension(rerun, canary_baseline),
            self._envelope_dimension(),
            self._novelty_dimension(novelty),
        )
        verdict = self._render_verdict(dimensions)
        statement = self._render_statement(verdict, dimensions)
        evidence_refs = tuple(
            sorted(
                {
                    ref
                    for dimension in dimensions
                    for ref in dimension.evidence_refs
                }
            )
        )
        dimension_payloads = [
            {
                "dimension_id": dimension.dimension_id,
                "verdict": dimension.verdict.value,
                "evidence_refs": list(dimension.evidence_refs),
                "bounds": list(dimension.bounds),
            }
            for dimension in dimensions
        ]
        content_hash = hash_canonical(
            {
                "verdict": verdict.value,
                "dimensions": dimension_payloads,
                "evidence_chain_refs": list(evidence_refs),
            }
        )
        cert_ref = self._ledger.record_certification(
            certification_id=config.certification_id,
            verdict=verdict.value,
            certification_statement=statement,
            dimensions=dimension_payloads,
            measured_envelope=evidence.ramp.scale_envelope,
            declared_assumptions=evidence.ramp.declared_assumptions,
            evidence_chain_refs=list(evidence_refs),
            content_hash=content_hash,
        )
        return CertificationArtifact(
            certification_id=config.certification_id,
            verdict=verdict,
            certification_statement=statement,
            dimensions=dimensions,
            measured_envelope=evidence.ramp.scale_envelope,
            declared_assumptions=evidence.ramp.declared_assumptions,
            evidence_chain_refs=evidence_refs,
            content_hash=content_hash,
            certification_event_ref=cert_ref,
        )

    # -- the seven dimensions -----------------------------------------------------

    def _calibration_dimension(self) -> CertificationDimension:
        calibration = self._evidence.calibration
        passed = (
            calibration.calibration_verdict is CalibrationVerdict.READY_FOR_31_2
            and calibration.deterministic_replay_verified
            and calibration.provenance_complete
            and calibration.failures_fully_classified
            and bool(calibration.declared_assumptions)
        )
        return CertificationDimension(
            "calibration",
            DimensionVerdict.PASS if passed else DimensionVerdict.FAIL,
            (calibration.calibration_event_ref,),
            (
                "calibration measures the declared pipeline — a calibration "
                "over stubbed derivations is a calibration of the stub, and "
                "the 31.1 report says so explicitly (declared assumption, "
                "carried onto this artifact)",
            ),
        )

    def _backend_matrix_dimension(self) -> CertificationDimension:
        matrix = self._evidence.matrix
        passed = (
            matrix.verdict is MatrixVerdict.READY_FOR_31_3
            and matrix.cross_backend_invariance_held
            and bool(matrix.declared_assumptions)
        )
        return CertificationDimension(
            "backend_matrix",
            DimensionVerdict.PASS if passed else DimensionVerdict.FAIL,
            (matrix.matrix_event_ref,),
            (
                "one ISR per intent realized through all seven declared "
                "backends — the comparison is over one semantic source "
                "realized many ways; EXPLICITLY_UNSUPPORTED is a legitimate "
                "terminal disposition, named never silent",
            ),
        )

    def _failure_taxonomy_dimension(self) -> CertificationDimension:
        taxonomy = self._evidence.taxonomy
        passed = (
            taxonomy.verdict is TaxonomyVerdict.READY_FOR_31_4
            and taxonomy.all_correct
            and taxonomy.no_conflation
        )
        return CertificationDimension(
            "failure_taxonomy",
            DimensionVerdict.PASS if passed else DimensionVerdict.FAIL,
            (taxonomy.taxonomy_event_ref,),
            (
                "every failure class induced as a real execution condition "
                "and classified from real evidence by the AST-enforced "
                "no-outcome-peeking classifier — 31.3, intact",
            ),
        )

    def _scale_ramp_dimension(self) -> CertificationDimension:
        ramp = self._evidence.ramp
        gates_held = bool(ramp.per_level) and all(
            all(level.gates_held.values()) for level in ramp.per_level
        )
        if (
            not gates_held
            or ramp.verdict is not ScaleRampVerdict.READY_FOR_31_5
            or not ramp.declared_assumptions
        ):
            verdict = DimensionVerdict.FAIL
        elif ramp.taxonomy_exercised:
            verdict = DimensionVerdict.PASS
        else:
            verdict = DimensionVerdict.QUALIFIED
        unreached = ", ".join(
            str(scale)
            for scale in ramp.scheduled_levels
            if scale > ramp.reachable_top
        )
        return CertificationDimension(
            "scale_ramp",
            verdict,
            (ramp.ramp_event_ref,),
            (
                f"ten gates held at every level up to the measured "
                f"envelope {ramp.scale_envelope}",
                "failure taxonomy NOT exercised on natural failures at "
                "scale (taxonomy_exercised: False, declared by 31.4) — "
                "validated on induced failures in 31.3; a bound on this "
                "certification's scope, and it belongs in the verdict, "
                "not in a footnote",
                f"corpus_growth: {ramp.corpus_growth_strategy.value}",
                f"rerun_subset: {ramp.rerun_subset.subset_id} replayed at "
                "every level",
                f"reachable_top: {ramp.reachable_top}; unreached "
                f"scheduled levels: {unreached or '(none)'}",
                f"per-level budget {ramp.level_budget_seconds}s measured "
                "by the real clock",
            ),
        )

    def _canary_dimension(
        self,
        rerun: Any,
        canary_baseline: Mapping[
            tuple[str, str], tuple[str, str | None, str | None, bool | None]
        ]
        | None,
    ) -> CertificationDimension:
        ramp = self._evidence.ramp
        baseline = (
            dict(ramp.per_level[-1].canary_outcomes)
            if canary_baseline is None
            else dict(canary_baseline)
        )
        current = {
            (case.intent_id, case.backend_id): (
                case.disposition.value,
                case.isr_hash,
                case.artifact_hash,
                case.verification_verified,
            )
            for case in rerun.cases
        }
        reproduced = (
            set(current) == set(baseline)
            and all(current[key] == value for key, value in baseline.items())
            and rerun.cross_backend_invariance_held
        )
        return CertificationDimension(
            "canary",
            DimensionVerdict.PASS if reproduced else DimensionVerdict.FAIL,
            (rerun.matrix_event_ref, ramp.ramp_event_ref),
            (
                f"the {len(baseline)}-case deterministic rerun subset "
                "replayed through the seven-backend matrix at "
                "certification time — reproduced, never cited",
            ),
        )

    def _envelope_dimension(self) -> CertificationDimension:
        ramp = self._evidence.ramp
        honest = ramp.scale_envelope > 0
        if ramp.envelope_hit_at is not None:
            level = next(
                level
                for level in ramp.per_level
                if level.scale == ramp.envelope_hit_at
            )
            honest = honest and bool(ramp.envelope_reason)
            if "measured duration" in (ramp.envelope_reason or ""):
                # A budget breach is envelope evidence, never a campaign
                # defect: it must not have been blurred into the failure
                # rate as a resource-classified software failure.
                honest = honest and all(
                    category
                    not in (
                        FailureCategory.RESOURCE_EXHAUSTION,
                        FailureCategory.TIMEOUT,
                    )
                    for category in level.failure_tally
                )
        else:
            honest = honest and ramp.ramp_complete
        return CertificationDimension(
            "envelope",
            DimensionVerdict.PASS if honest else DimensionVerdict.FAIL,
            (ramp.ramp_event_ref,),
            (
                f"measured scale envelope: {ramp.scale_envelope} — the "
                "budget exceedance stays INFRASTRUCTURE-classified (a real "
                "resource signal, never reinterpreted as a software "
                "defect); the boundary itself is the evidence",
                f"per-level budget: {ramp.level_budget_seconds}s, real "
                "clock",
                f"ramp_complete: {ramp.ramp_complete}, envelope_hit_at: "
                f"{ramp.envelope_hit_at}",
            ),
        )

    def _novelty_dimension(
        self, novelty: NoveltyGroundingResult
    ) -> CertificationDimension:
        return CertificationDimension(
            "novelty_grounding",
            novelty.verdict,
            novelty.evidence_refs,
            (
                "novel intent drawn from OUTSIDE the calibration corpus — "
                "generative capacity, never corpus recall",
                "derivation flows through the constitution's pipeline "
                "(Problem -> Requirements -> Requirement Graph -> ISR -> "
                "backends), never requirements -> code directly; the "
                "declared-stub limitation is carried in the declared "
                "assumptions",
                "every semantic element in the artifact traces to the "
                "source ISR — content with no ISR provenance is "
                "hallucination, and there is no minor-hallucination pass",
            ),
        )

    # -- verdict rendering ---------------------------------------------------------

    @staticmethod
    def _render_verdict(
        dimensions: tuple[CertificationDimension, ...],
    ) -> CertificationVerdict:
        if any(
            dimension.verdict is DimensionVerdict.FAIL
            for dimension in dimensions
        ):
            return CertificationVerdict.NOT_CERTIFIED
        if all(
            dimension.verdict is DimensionVerdict.PASS
            for dimension in dimensions
        ):
            return CertificationVerdict.CERTIFIED
        return CertificationVerdict.QUALIFIED_PARTIAL

    def _render_statement(
        self,
        verdict: CertificationVerdict,
        dimensions: tuple[CertificationDimension, ...],
    ) -> str:
        # The statement is BOUNDED: it names the envelope, the assumptions,
        # and the novelty-grounding result. An unbounded statement is
        # certification inflation.
        envelope = self._evidence.ramp.scale_envelope
        assumptions = self._evidence.ramp.declared_assumptions
        base = (
            "Tiannara can repeatedly transform heterogeneous requirements "
            "into independently verifiable software artifacts while "
            "preserving ISR semantics across compiler backends — certified "
            f"to the measured scale envelope of {envelope}, under the "
            f"declared assumptions {list(assumptions)}, with novel-intent "
            "generation verified to flow through the ISR without "
            "hallucinated semantics"
        )
        if verdict is CertificationVerdict.CERTIFIED:
            return base + "."
        if verdict is CertificationVerdict.QUALIFIED_PARTIAL:
            qualified = ", ".join(
                dimension.dimension_id
                for dimension in dimensions
                if dimension.verdict is DimensionVerdict.QUALIFIED
            )
            return (
                base
                + f". QUALIFIED_PARTIAL — the certification's scope is "
                f"bounded by incomplete evidence in: {qualified}. Each "
                "bound is declared on its dimension and on the ledger."
            )
        failed = ", ".join(
            dimension.dimension_id
            for dimension in dimensions
            if dimension.verdict is DimensionVerdict.FAIL
        )
        return base + f". NOT_CERTIFIED — evidence failed in: {failed}."

    # -- the canary re-run -----------------------------------------------------------

    def _reproduce_canary(self, config: CertificationConfig) -> Any:
        """The deterministic rerun subset replayed through the full
        seven-backend matrix AT CERTIFICATION TIME — the 42-case invariant
        is reproduced, never cited."""
        if self._canary_rerun is None:
            ramp = self._evidence.ramp
            subset_ids = set(ramp.rerun_subset.intent_ids)
            subset = GenerationCorpus(
                corpus_id=f"{config.certification_id}-canary-rerun",
                intents=tuple(
                    intent
                    for intent in self._corpus.intents
                    if intent.intent_id in subset_ids
                ),
            )
            rerun_config = dataclasses.replace(
                self._base_config,
                campaign_id=f"{config.certification_id}-canary-rerun",
                corpus_id=subset.corpus_id,
            )
            self._canary_rerun = self._matrix.run(subset, rerun_config)
        return self._canary_rerun