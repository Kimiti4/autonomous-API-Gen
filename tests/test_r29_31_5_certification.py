"""R2.10.31.5 — Certification: consume the evidence, earn the word.

31.1-31.4 accumulated the evidence; 31.5 certifies it. The certifier
ASSEMBLES and VERIFIES the evidence chain — it never re-runs the campaign
in a way that could produce different evidence to certify. The two
deliberate exceptions are the canary RE-RUN (a certification that trusts
yesterday's evidence without reproducing it is one step from trusting
yesterday's claim) and the novelty-grounding check (can the platform
develop NOVEL software without going against the ISR and without
hallucinating — the constitution's foundational principle made
operational).

The verdict is bounded, never inflated: CERTIFIED / QUALIFIED_PARTIAL /
NOT_CERTIFIED, with every bound declared in the verdict, not in a
footnote. In the honest run the verdict is QUALIFIED_PARTIAL — 31.4
observed zero failures, so the taxonomy was never exercised on natural
failures at scale (taxonomy_exercised: False, already declared): not a
defect, a bound on the certification's scope.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from tiannara.application.campaign.backend_matrix import MatrixHarness
from tiannara.application.campaign.calibration import CalibrationHarness
from tiannara.application.campaign.certification import (
    CertificationArtifact,
    CertificationConfig,
    CertificationDimension,
    CertificationEvidence,
    CertificationHarness,
    CertificationVerdict,
    DimensionVerdict,
    NoveltyGroundingCheck,
    artifact_semantic_elements,
    hash_canonical,
    isr_semantic_elements,
)
from tiannara.application.campaign.corpus import (
    CorpusIntent,
    ProjectCategory,
)
from tiannara.application.campaign.failure_taxonomy_validation import (
    FailureInjector,
    INJECTION_ASSUMPTIONS,
    TaxonomyClassifier,
    TaxonomyValidationHarness,
)
from tiannara.application.campaign.harness import target_for
from tiannara.application.campaign.scale_ramp import (
    CorpusBuilder,
    ScaleRampHarness,
    SCALE_LEVELS,
)
from tiannara.application.evolution.ledger import EventType

from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
from .test_r29_31_4_scale_ramp import RERUN_SUBSET

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def novel_intent() -> CorpusIntent:
    """A genuinely NEW intent, outside the 26 calibration seeds — the
    novelty check must exercise generative capacity, never corpus
    recall."""
    return CorpusIntent(
        intent_id="inventory-lot-01",
        category=ProjectCategory.CRUD_SAAS,
        problem_statement=(
            "Operate a perishable inventory system: stock lots, expiry "
            "tracking, spoilage alerts, and recall tracing."
        ),
        complexity_tier=2,
        acceptance_semantics=(
            "the system must demonstrably satisfy the declared problem",
        ),
        semantic_shape_hints=(),
    )


class CertificationRig:
    """The full 31.1-31.4 evidence chain on ONE ledger, plus the
    certification machinery. The ramp dominates the runtime (the real
    26 -> 100 -> 500 climb); everything else is assembled from it."""

    def __init__(self) -> None:
        self.base = CampaignReadinessHarness()
        calibration = CalibrationHarness(
            self.base.harness, self.base.corpus, self.base.ledger
        )
        self.calibration = calibration.run(self.base.config)
        self.matrix = MatrixHarness(
            intent_pipeline=self.base.intent_pipeline,
            registry=self.base.registry,
            evaluator=self.base.evaluator,
            verifier=self.base.verifier,
            conformance_registry=self.base.conformance_registry,
            ledger=self.base.ledger,
            declared_assumptions=self.calibration.declared_assumptions,
        ).run(self.base.corpus, self.base.config)
        injector = FailureInjector(
            intent_pipeline=self.base.intent_pipeline,
            registry=self.base.registry,
            evaluator=self.base.evaluator,
            verifier=self.base.verifier,
            conformance_registry=self.base.conformance_registry,
            ledger=self.base.ledger,
        )
        self.taxonomy = TaxonomyValidationHarness(
            classifier=TaxonomyClassifier(),
            injector=injector,
            ledger=self.base.ledger,
            declared_assumptions=(
                self.calibration.declared_assumptions + INJECTION_ASSUMPTIONS
            ),
        ).run(
            self.base.corpus,
            ("react", "fastapi", "postgres", "terraform",
             "cicd", "pytest", "markdown"),
            self.base.config,
        )
        self.ramp = ScaleRampHarness(
            campaign_harness=self.base.harness,
            intent_pipeline=self.base.intent_pipeline,
            registry=self.base.registry,
            evaluator=self.base.evaluator,
            verifier=self.base.verifier,
            conformance_registry=self.base.conformance_registry,
            ledger=self.base.ledger,
            corpus_builder=CorpusBuilder(self.base.corpus),
            taxonomy_classifier=TaxonomyClassifier(),
            rerun_subset=RERUN_SUBSET,
            declared_assumptions=self.calibration.declared_assumptions,
            scale_levels=SCALE_LEVELS,
            reachable_top=500,
            level_budget_seconds=300,
        ).run(self.base.config)
        self.evidence = CertificationEvidence(
            self.calibration, self.matrix, self.taxonomy, self.ramp
        )
        self.novelty_check = NoveltyGroundingCheck(
            self.base.intent_pipeline, self.base.compilation, self.base.verifier
        )
        self.novel = novel_intent()
        self._artifact: CertificationArtifact | None = None
        self._novelty_result = None

    def make_certifier(self, canary_baseline=None) -> CertificationHarness:
        return CertificationHarness(
            evidence_store=self.evidence,
            novelty_check=self.novelty_check,
            intent_pipeline=self.base.intent_pipeline,
            registry=self.base.registry,
            evaluator=self.base.evaluator,
            verifier=self.base.verifier,
            conformance_registry=self.base.conformance_registry,
            ledger=self.base.ledger,
            corpus=self.base.corpus,
            base_config=self.base.config,
            declared_assumptions=self.calibration.declared_assumptions,
        )

    def certify(self, canary_baseline=None) -> CertificationArtifact:
        if self._artifact is None:
            self._artifact = self.make_certifier(canary_baseline).certify(
                CertificationConfig("cert-31-5", self.novel)
            )
        return self._artifact

    def novelty(self):
        if self._novelty_result is None:
            self._novelty_result = self.novelty_check.check(self.novel)
        return self._novelty_result


@pytest.fixture(scope="module")
def certification_rig() -> CertificationRig:
    return CertificationRig()


def test_no_certified_verdict_before_final_gate(certification_rig):
    """Invariant 1: CERTIFIED appears only at the final certification
    gate. Every prior phase's verdict — in its report AND on its ledger
    event — is READY_FOR_X, never CERTIFIED."""
    rig = certification_rig
    prior_verdicts = (
        rig.calibration.calibration_verdict,
        rig.matrix.verdict,
        rig.taxonomy.verdict,
        rig.ramp.verdict,
    )
    assert all("CERTIFIED" not in verdict.value for verdict in prior_verdicts)
    for event in rig.base.ledger.events():
        if event.event_type in (
            EventType.CALIBRATION,
            EventType.MATRIX,
            EventType.TAXONOMY_VALIDATION,
            EventType.SCALE_RAMP,
        ):
            payload = event.payload or {}
            recorded = payload.get("calibration_verdict") or payload.get(
                "verdict"
            ) or payload.get("scale_ramp_verdict")
            assert "CERTIFIED" not in recorded


def test_measured_envelope_is_part_of_evidence(certification_rig):
    """Invariant 2: 31.4's measured envelope is first-class certification
    content, never a footnote."""
    artifact = certification_rig.certify()
    assert artifact.measured_envelope == certification_rig.ramp.scale_envelope
    assert artifact.measured_envelope > 0
    assert str(artifact.measured_envelope) in artifact.certification_statement


def test_budget_exceedance_remains_honestly_classified(certification_rig):
    """Invariant 3: the envelope stay honest. A budget breach is a real
    resource signal — measured, named, and NEVER blurred into the failure
    rate as a resource-classified software failure. (Machine-measured: on
    a fast machine the ramp completes; on a slow one it stops at the
    measured envelope. Both are honest, and both are certified.)"""
    rig = certification_rig
    ramp = rig.ramp
    if ramp.envelope_hit_at is not None:
        level = next(
            level for level in ramp.per_level if level.scale == ramp.envelope_hit_at
        )
        assert ramp.envelope_reason
        if "measured duration" in ramp.envelope_reason:
            assert all(
                category.value
                not in ("RESOURCE_EXHAUSTION", "TIMEOUT")
                for category in level.failure_tally
            )
    else:
        assert ramp.ramp_complete is True
    artifact = rig.certify()
    envelope_dim = next(
        d for d in artifact.dimensions if d.dimension_id == "envelope"
    )
    assert envelope_dim.verdict is DimensionVerdict.PASS
    assert any("INFRASTRUCTURE-classified" in bound for bound in envelope_dim.bounds)


def test_canary_invariant_reproduced(certification_rig):
    """Invariant 4: the 42/42 semantic canary is RE-RUN at certification
    time, never cited."""
    rig = certification_rig
    artifact = rig.certify()
    canary = next(d for d in artifact.dimensions if d.dimension_id == "canary")
    assert canary.verdict is DimensionVerdict.PASS
    rerun_event = rig.base.ledger.event_by_ref(canary.evidence_refs[0])
    assert rerun_event is not None
    assert rerun_event.event_type is EventType.MATRIX
    rerun_cases = rerun_event.payload["cases"]
    assert len(rerun_cases) == len(RERUN_SUBSET.intent_ids) * 7
    assert all(case["disposition"] == "VERIFIED_COMPILATION" for case in rerun_cases)


def test_calibration_assumptions_provenance_linked(certification_rig):
    """Invariant 5: the declared assumptions carry through, bound to their
    origin — from the 31.1 calibration report, through the ramp, onto the
    certification artifact. Never re-derived, never dropped."""
    rig = certification_rig
    artifact = rig.certify()
    assert all(
        assumption in artifact.declared_assumptions
        for assumption in rig.calibration.declared_assumptions
    )
    assert any("DECLARED deterministic stub" in a for a in artifact.declared_assumptions)
    assert artifact.declared_assumptions == rig.ramp.declared_assumptions


def test_backend_matrix_evidence_chain_resolvable(certification_rig):
    """Invariant 6: every dimension's evidence refs resolve to real ledger
    events — each certification claim is reconstructible from the chain."""
    artifact = certification_rig.certify()
    for dimension in artifact.dimensions:
        for ref in dimension.evidence_refs:
            assert (
                certification_rig.base.ledger.event_by_ref(ref) is not None
            ), ref


def test_taxonomy_validation_intact(certification_rig):
    """Invariant 7: the 910-case taxonomy validation remains part of the
    evidence — intact, chain-anchored, consumed by the certification."""
    rig = certification_rig
    artifact = rig.certify()
    taxonomy_dim = next(
        d for d in artifact.dimensions if d.dimension_id == "failure_taxonomy"
    )
    assert taxonomy_dim.verdict is DimensionVerdict.PASS
    assert rig.taxonomy.all_correct is True
    assert rig.taxonomy.no_conflation is True
    assert len(rig.taxonomy.cases) == 910


def test_every_claim_reconstructible_from_ledger(certification_rig):
    """Invariant 8: the artifact's content hash commits to its evidence
    references; the whole chain is intact; the certification event carries
    the same claim."""
    rig = certification_rig
    artifact = rig.certify()
    assert rig.base.ledger.verify_event_chain() is True
    expected = hash_canonical(
        {
            "verdict": artifact.verdict.value,
            "dimensions": [
                {
                    "dimension_id": d.dimension_id,
                    "verdict": d.verdict.value,
                    "evidence_refs": list(d.evidence_refs),
                    "bounds": list(d.bounds),
                }
                for d in artifact.dimensions
            ],
            "evidence_chain_refs": list(artifact.evidence_chain_refs),
        }
    )
    assert artifact.content_hash == expected
    event = rig.base.ledger.event_by_ref(artifact.certification_event_ref)
    assert event is not None
    assert event.payload["content_hash"] == artifact.content_hash
    assert event.payload["measured_envelope"] == artifact.measured_envelope
    assert event.payload["verdict"] == artifact.verdict.value


def test_no_retroactive_weakening(certification_rig):
    """Invariant 9: no criterion can be weakened to fit the evidence.
    Structural: the certification machinery has no criterion-mutation
    surface."""
    for cls in (CertificationHarness, NoveltyGroundingCheck):
        tree = ast.parse(inspect.getsource(cls))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = ast.unparse(node.func)
                assert not any(
                    m in fn for m in ("relax_criterion", "weaken", "adjust_threshold")
                ), fn


def test_novel_intent_is_outside_calibration_corpus(certification_rig):
    """The novelty check exercises generative capacity, not corpus
    recall."""
    rig = certification_rig
    seed_ids = set(CorpusBuilder(rig.base.corpus).seed_intent_ids())
    assert rig.novel.intent_id not in seed_ids
    assert rig.novel.intent_id not in {
        intent.intent_id for intent in rig.base.corpus.intents
    }


def test_novel_intent_flows_through_isr(certification_rig):
    """Novel software must flow through the ISR — never requirements ->
    code directly."""
    result = certification_rig.novelty()
    assert result.derivation_flowed_through_isr is True


def test_novel_software_conforms_to_isr(certification_rig):
    """Novel software must not go against the ISR: it verifies against
    its source."""
    result = certification_rig.novelty()
    assert result.conforms_to_isr is True


def test_novel_software_does_not_hallucinate(certification_rig):
    """Every semantic element in the novel artifact traces to the ISR.
    Untraceable content is hallucination — the generator asserting what
    the ISR never said. There is no minor-hallucination pass."""
    result = certification_rig.novelty()
    assert result.grounding.grounded is True
    assert result.grounding.untraced_semantics == ()
    novelty_dim = next(
        d
        for d in certification_rig.certify().dimensions
        if d.dimension_id == "novelty_grounding"
    )
    assert novelty_dim.verdict is DimensionVerdict.PASS


def test_grounding_rejects_foreign_semantics(certification_rig):
    """The grounding comparison is real, not tautological: a semantic
    element with no ISR provenance is detected and named."""
    rig = certification_rig
    isr = rig.base.intent_pipeline.derive(rig.novel)
    compiled = rig.base.compilation.compile(
        isr, target_for(rig.novel.category)
    )
    foreign = dict(compiled.artifact)
    foreign["coverage"] = list(compiled.artifact["coverage"]) + [
        {
            "capability_id": "capability:foreign-not-declared",
            "support": "SUPPORTED",
            "note": "tampered — content the ISR never said",
        }
    ]
    isr_semantics = isr_semantic_elements(isr)
    artifact_semantics = artifact_semantic_elements(foreign)
    untraced = artifact_semantics - isr_semantics
    assert untraced
    assert any(
        "capability:foreign-not-declared" in item
        for item in (
            f"{kind}:{content}" for (kind, content) in untraced
        )
    )


def test_verdict_bounded_not_inflated(certification_rig):
    """The certification statement names its bounds — the envelope and the
    assumptions — and the verdict space is exactly the declared three."""
    artifact = certification_rig.certify()
    assert str(artifact.measured_envelope) in artifact.certification_statement
    assert "declared assumptions" in artifact.certification_statement
    assert artifact.verdict in (
        CertificationVerdict.CERTIFIED,
        CertificationVerdict.QUALIFIED_PARTIAL,
        CertificationVerdict.NOT_CERTIFIED,
    )


def test_qualification_belongs_in_the_verdict(certification_rig):
    """The honest verdict is QUALIFIED_PARTIAL: 31.4 observed zero
    failures, so the taxonomy was never exercised on natural failures at
    scale — a bound on the certification's scope, declared in the verdict
    and in the scale_ramp dimension's bounds, never hidden in a footnote."""
    artifact = certification_rig.certify()
    assert artifact.verdict is CertificationVerdict.QUALIFIED_PARTIAL
    assert "QUALIFIED_PARTIAL" in artifact.certification_statement
    scale_ramp_dim = next(
        d for d in artifact.dimensions if d.dimension_id == "scale_ramp"
    )
    assert scale_ramp_dim.verdict is DimensionVerdict.QUALIFIED
    assert any(
        "taxonomy_exercised: False" in bound for bound in scale_ramp_dim.bounds
    )


def test_certified_verdict_reachable_when_all_pass():
    """CERTIFIED is earned, never issued by default: the pure verdict
    renderer returns CERTIFIED only when every dimension passes."""
    dimensions = tuple(
        CertificationDimension(f"d{i}", DimensionVerdict.PASS, (), ())
        for i in range(7)
    )
    assert (
        CertificationHarness._render_verdict(dimensions)
        is CertificationVerdict.CERTIFIED
    )


def test_not_certified_when_canary_drifts(certification_rig):
    """A canary that genuinely drifts MUST refuse certification: the re-run
    is compared against the baseline, and a single differing artifact hash
    fails the canary dimension — NOT_CERTIFIED, with the failure named."""
    rig = certification_rig
    baseline = dict(rig.ramp.per_level[-1].canary_outcomes)
    drifted = dict(baseline)
    drifted[("credit-02", "react")] = (
        drifted[("credit-02", "react")][0],
        drifted[("credit-02", "react")][1],
        "0" * 64,
        True,
    )
    artifact = rig.make_certifier().certify(
        CertificationConfig("cert-31-5-drifted", rig.novel),
        canary_baseline=drifted,
    )
    assert artifact.verdict is CertificationVerdict.NOT_CERTIFIED
    canary_dim = next(
        d for d in artifact.dimensions if d.dimension_id == "canary"
    )
    assert canary_dim.verdict is DimensionVerdict.FAIL
    assert "NOT_CERTIFIED" in artifact.certification_statement
    assert "canary" in artifact.certification_statement


def test_certification_event_enters_ledger(certification_rig):
    """The CertificationArtifact is chain-anchored: the certification event
    is on the ledger with the same verdict, dimensions, envelope, and
    content hash, and the chain stays intact."""
    rig = certification_rig
    artifact = rig.certify()
    event = rig.base.ledger.event_by_ref(artifact.certification_event_ref)
    assert event is not None
    assert event.event_type is EventType.CERTIFICATION
    assert event.subject_id == artifact.certification_id
    assert event.payload["verdict"] == artifact.verdict.value
    assert event.payload["measured_envelope"] == artifact.measured_envelope
    assert len(event.payload["dimensions"]) == len(artifact.dimensions)
    assert rig.base.ledger.verify_event_chain() is True


def test_matrix_identity_unchanged(certification_rig):
    """Option A (twenty-second use): certification changes no carrier and
    no matrix cell — the recipe ISR is byte-identical."""
    assert certification_rig.base.matrix_summary() == (12, 18, 0, 0)
    assert certification_rig.base.recipe_isr_hash() == RECIPE_HASH