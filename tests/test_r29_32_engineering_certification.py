"""R2.10.32 — Engineering Certification: gates, not averages.

The certification harness measures ONE artifact against the ISR that
produced it under the declared R2.10.32 contract. ISR Conformance is
dispositive and checked FIRST; the seven gradable dimensions are analyzed
over the artifact's real evidence (declared coverage, projection content,
bundle source) by deterministic plug-in analyzers; every dimension result
and every certificate is chain-anchored; and the certifier never mutates
anything — remediation is the EvolutionaryQualityLoop's job (ISR mutation
through the declared operators, then re-certification).

The honest runs in this suite:

  * the REFERENCE artifact (full derived ISR) certifies — the control.
  * the FASTAPI artifact (full ISR) is NOT_CERTIFIED on conformance: its
    own declared coverage is UNSUPPORTED/PARTIAL for most mandatory
    obligations — the locally-perfect-but-architecturally-wrong case.
  * the FASTAPI artifact over a behavior-only ISR reaches the gradable
    dimensions and is NOT_CERTIFIED structurally: wildcard CORS with
    credentialed auth is a CRITICAL security violation.
  * the POSTGRES artifact over a migration-only ISR passes conformance but
    fails EVOLVABILITY: its abstraction is not justified (1 of 5 expressed
    semantics realized) even though its simulated evolution cost is cheap
    — the complexity gate conjoins, over-abstraction cannot game it.
  * the loop starts from the behavior-only ISR and reaches CERTIFIED in
    two declared mutations (reliability, then deployment semantics).
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect

import pytest

from tiannara.application.campaign.harness import target_for
from tiannara.application.compilation.reference_backend import (
    ReferenceCompilerBackend,
)
from tiannara.application.evolution.ledger import EventType
from tiannara.application.quality.engineering_certification import (
    EngineeringCertificationHarness,
    EvolutionaryQualityLoop,
    default_dimension_analyzers,
)
from tiannara.application.quality.engineering_contract import (
    GRADABLE_DIMENSIONS,
    EngineeringDimension,
    EngineeringVerdict,
    FindingSeverity,
    default_engineering_contract,
)
from constitutional_architecture.isr.semantics.projection import canonicalize

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness


def _minimal_isr(isr):
    """A behavior-only ISR: business capabilities and workflows, nothing
    else. Declared instrumentation — the corpus derivation stripped through
    the ISR's own carrier surface."""
    system = isr.system
    modules = tuple(
        dataclasses.replace(m, data_migrations=(), temporal_constraints=())
        for m in system.modules
    )
    return isr.with_system(
        dataclasses.replace(
            system,
            requirements=(),
            acceptance_criteria=(),
            architectural_boundaries=(),
            reliability_requirements=(),
            deployment_intents=(),
            testing_anchors=(),
            protected_regions=(),
            evolution_policies=(),
            documentation_intents=(),
            evolution_objectives=(),
            modules=modules,
        )
    )


def _migration_probe_isr(isr):
    """A migration+documentation+evolution-objectives ISR: the only
    mandatory carrier is data_migrations (postgres SUPPORTED), the others
    are advisory — conformance passes while the abstraction is mostly
    unrealized."""
    system = isr.system
    modules = tuple(
        dataclasses.replace(m, temporal_constraints=())
        for m in system.modules
    )
    return isr.with_system(
        dataclasses.replace(
            system,
            requirements=(),
            acceptance_criteria=(),
            architectural_boundaries=(),
            reliability_requirements=(),
            deployment_intents=(),
            testing_anchors=(),
            protected_regions=(),
            evolution_policies=(),
            modules=modules,
        )
    )


class EngineeringRig:
    """The Phase 32 machinery wired behind one readiness harness."""

    def __init__(self) -> None:
        self.base = CampaignReadinessHarness()
        self.ledger = self.base.ledger
        self.contract = default_engineering_contract()
        self.certification = EngineeringCertificationHarness(
            contract=self.contract,
            analyzers=default_dimension_analyzers(),
            ledger=self.ledger,
            certificate_prefix="eng-suite",
            evolution_id="r2.10.32-suite",
        )
        self.billing = next(
            intent
            for intent in self.base.corpus.intents
            if intent.intent_id == "billing-01"
        )
        self.workspace = next(
            intent
            for intent in self.base.corpus.intents
            if intent.intent_id == "workspace-02"
        )
        self.billing_isr = self.base.intent_pipeline.derive(self.billing)
        self.workspace_isr = self.base.intent_pipeline.derive(self.workspace)
        self.target = target_for(self.billing.category)
        self.reference = ReferenceCompilerBackend(
            backend_id="reference", backend_version="32.0.0"
        )
        self.fastapi = self.base.registry.adapter("fastapi")
        self.postgres = self.base.registry.adapter("postgres")

    def reference_artifact(self, isr=None):
        return self.reference.compile(
            isr or self.billing_isr, self.target
        ).artifact

    def fastapi_artifact(self, isr=None):
        return self.fastapi.compile(isr or self.billing_isr, self.target).artifact

    def postgres_artifact(self, isr):
        return self.postgres.compile(isr, self.target).artifact

    def certify(self, artifact, isr=None, *, generation_id="gen-0"):
        return self.certification.certify(
            artifact, isr or self.billing_isr, generation_id=generation_id
        )

    def minimal_isr(self):
        return _minimal_isr(self.billing_isr)

    def migration_probe_isr(self):
        return _migration_probe_isr(self.billing_isr)

    def loop(self, compile_fn=None):
        compile_fn = compile_fn or (lambda isr: self.reference_artifact(isr))
        return EvolutionaryQualityLoop(self.certification, compile_fn, self.ledger)


@pytest.fixture
def engineering_rig() -> EngineeringRig:
    return EngineeringRig()


# -- dispositive conformance ---------------------------------------------------


def test_conformance_is_dispositive_and_first(engineering_rig):
    """Good artifact: conformance enforced, seven gradable dimensions
    evaluated. Wrong-source artifact: NOT_CERTIFIED before any dimension
    runs, with the divergence named."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    assert good.isr_conformance.all_mandatory_enforced is True
    assert good.isr_conformance.source_bound is True
    assert len(good.dimensions) == 7

    wrong = rig.certify(rig.reference_artifact(rig.workspace_isr))
    assert wrong.verdict is EngineeringVerdict.NOT_CERTIFIED
    assert wrong.dimensions == ()
    assert wrong.isr_conformance.source_bound is False
    assert wrong.critical_violations
    assert all(
        v.dimension is EngineeringDimension.ISR_CONFORMANCE
        for v in wrong.critical_violations
    )


def test_certified_only_when_all_dimensions_meet_bars(engineering_rig):
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    assert good.verdict is EngineeringVerdict.CERTIFIED
    assert all(result.meets for result in good.dimensions)


def test_locally_perfect_architecturally_wrong(engineering_rig):
    """The fastapi artifact is locally well-formed (hexagonal layers,
    acyclic) but architecturally wrong for this ISR: its own declared
    coverage leaves most mandatory obligations UNSUPPORTED or PARTIAL —
    conformance names that and certification stops."""
    rig = engineering_rig
    certificate = rig.certify(rig.fastapi_artifact())
    assert certificate.verdict is EngineeringVerdict.NOT_CERTIFIED
    assert certificate.dimensions == ()
    violated_kinds = {
        violation.obligation_id.split(":")[0]
        for violation in certificate.critical_violations
    }
    assert {
        "requirement",
        "migration",
        "testing_anchor",
        "protected_region",
        "reliability",
    } <= violated_kinds
    for violation in certificate.critical_violations:
        assert violation.severity is FindingSeverity.CRITICAL


def test_gates_not_averages(engineering_rig):
    """No score anywhere: the verdict is rendered from the gates, and the
    certificate carries per-gate booleans, not a number."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    assert [result.dimension for result in good.dimensions] == list(
        GRADABLE_DIMENSIONS
    )
    for result in good.dimensions:
        assert isinstance(result.meets, bool)
    assert not hasattr(good, "score")
    assert not any(hasattr(result, "score") for result in good.dimensions)
    assert good.verdict in (
        EngineeringVerdict.CERTIFIED,
        EngineeringVerdict.QUALIFIED_PARTIAL,
        EngineeringVerdict.NOT_CERTIFIED,
    )


def test_critical_violation_structurally_blocks(engineering_rig):
    """A CRITICAL finding in ANY dimension is structurally dispositive,
    even when conformance passed. The fastapi artifact over a behavior-only
    ISR: wildcard CORS + allow_credentials + OAuth bearer is a CRITICAL
    security violation."""
    rig = engineering_rig
    isr = rig.minimal_isr()
    certificate = rig.certify(rig.fastapi_artifact(isr), isr=isr)
    assert certificate.verdict is EngineeringVerdict.NOT_CERTIFIED
    assert len(certificate.dimensions) == 7
    assert any(
        violation.dimension is EngineeringDimension.SECURITY
        and violation.severity is FindingSeverity.CRITICAL
        for violation in certificate.critical_violations
    )
    security = next(
        result
        for result in certificate.dimensions
        if result.dimension is EngineeringDimension.SECURITY
    )
    assert any(
        finding.severity is FindingSeverity.CRITICAL
        for finding in security.findings
    )


# -- gradable dimensions --------------------------------------------------------


def test_failure_coverage_scenario_driven(engineering_rig):
    """FAILURE_ENGINEERING is scenario-based: the full-ISR reference
    artifact identifies >= 3 scenarios (reliability, migration, deployment
    rollback) and handles every one; an ISR declaring no failure scenarios
    fails the gate with a named MAJOR — never a vacuous pass."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    coverage = next(
        result
        for result in good.dimensions
        if result.dimension is EngineeringDimension.FAILURE_ENGINEERING
    ).coverage
    assert coverage.identified >= 3
    assert coverage.handled == coverage.identified
    assert coverage.coverage == 1.0

    isr = rig.minimal_isr()
    minimal = rig.certify(rig.reference_artifact(isr), isr=isr)
    assert minimal.verdict is EngineeringVerdict.QUALIFIED_PARTIAL
    failure_engineering = next(
        result
        for result in minimal.dimensions
        if result.dimension is EngineeringDimension.FAILURE_ENGINEERING
    )
    assert any(
        finding.severity is FindingSeverity.MAJOR
        and "no failure scenarios declared" in finding.description
        for finding in failure_engineering.findings
    )


def test_evolvability_not_gameable_by_over_abstraction(engineering_rig):
    """EVOLVABILITY conjoins the complexity gate: the postgres artifact
    over a migration-only ISR has a CHEAP simulated evolution cost but an
    unjustified abstraction (1 of 5 expressed semantics realized) — the
    gate fails and names the over-abstraction."""
    rig = engineering_rig
    isr = rig.migration_probe_isr()
    certificate = rig.certify(rig.postgres_artifact(isr), isr=isr)
    assert certificate.verdict is EngineeringVerdict.QUALIFIED_PARTIAL
    evolvability = next(
        result
        for result in certificate.dimensions
        if result.dimension is EngineeringDimension.EVOLVABILITY
    )
    assert evolvability.coverage.evolution_cost <= 0.5
    assert evolvability.coverage.abstraction_justified is False
    assert evolvability.coverage.evolvable_under is False
    assert any(
        finding.severity is FindingSeverity.MAJOR
        and "abstraction not justified" in finding.description
        for finding in evolvability.findings
    )


# -- evidence binding -----------------------------------------------------------


def test_every_dimension_evidence_bound(engineering_rig):
    """Each gradable dimension's result is bound to a chain-anchored,
    intact ENGINEERING_DIMENSION event."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    for result in good.dimensions:
        assert result.evidence_refs, result.dimension
        for ref in result.evidence_refs:
            event = rig.ledger.event_by_ref(ref)
            assert event is not None
            assert event.is_intact()
            assert event.event_type is EventType.ENGINEERING_DIMENSION
            assert event.payload["dimension"] == result.dimension.value


def test_certificate_chain_anchored(engineering_rig):
    """The certificate's content hash commits to its content; the chain
    event carries the same content; the whole chain verifies."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    event = rig.ledger.event_by_ref(good.certificate_event_ref)
    assert event is not None
    assert event.event_type is EventType.ENGINEERING_CERTIFICATION
    assert event.payload["verdict"] == good.verdict.value
    assert event.payload["content_hash"] == good.content_hash
    assert event.payload["certificate_content"] == good.content()
    expected = hashlib.sha256(
        canonicalize(good.content()).encode("utf-8")
    ).hexdigest()
    assert good.content_hash == expected
    assert rig.ledger.verify_event_chain() is True


def test_vacuity_is_named_never_blurred(engineering_rig):
    """Evidence-limited dimensions pass their gates with an ADVISORY that
    names the absence — vacuity is named, never blurred."""
    rig = engineering_rig
    good = rig.certify(rig.reference_artifact())
    implementation = next(
        result
        for result in good.dimensions
        if result.dimension is EngineeringDimension.IMPLEMENTATION
    )
    assert implementation.insufficient_evidence is True
    assert any(
        finding.severity is FindingSeverity.ADVISORY
        and "insufficient evidence" in finding.description
        for finding in implementation.findings
    )
    security = next(
        result
        for result in good.dimensions
        if result.dimension is EngineeringDimension.SECURITY
    )
    assert security.insufficient_evidence is True
    assert good.isr_conformance.advisory_notes


# -- the certifier is measurement-only -------------------------------------------


def test_measures_never_modify(engineering_rig):
    """Certifying never mutates the artifact or the ISR, and re-certifying
    the identical input records nothing new — the chain stays idempotent."""
    rig = engineering_rig
    artifact = rig.reference_artifact()
    isr = rig.billing_isr
    snapshot = canonicalize(artifact)
    first = rig.certify(artifact, isr=isr)
    second = rig.certify(artifact, isr=isr)
    assert canonicalize(artifact) == snapshot
    assert first.content_hash == second.content_hash
    assert first.content() == second.content()
    certificate_events = [
        event.event_id
        for event in rig.ledger.events()
        if event.event_type is EventType.ENGINEERING_CERTIFICATION
    ]
    assert len(certificate_events) == len(set(certificate_events))
    assert rig.ledger.verify_event_chain() is True


def test_certification_has_no_mutation_surface(engineering_rig):
    """Structural: the certifier cannot mutate anything — it has no
    ISR-mutation or artifact-editing surface."""
    tree = ast.parse(inspect.getsource(EngineeringCertificationHarness))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert not any(
                marker in fn for marker in ("mutate", "with_system", "set_")
            ), fn


# -- the contract ------------------------------------------------------------------


def test_declared_assumptions_carry_gate_calibration(engineering_rig):
    """The gate calibration is declared, never hidden: every gate carries a
    threshold and a rationale, the dispositive gate is ISR_CONFORMANCE and
    only it, and the contract records its calibration basis."""
    rig = engineering_rig
    contract = rig.contract
    assert len(contract.gates) == 8
    for gate in contract.gates:
        assert gate.threshold
        assert gate.rationale
    dispositive = contract.dispositive_gate()
    assert dispositive.dimension is EngineeringDimension.ISR_CONFORMANCE
    assert dispositive.is_dispositive is True
    assert all(
        not gate.is_dispositive
        for gate in contract.gates
        if gate.dimension is not EngineeringDimension.ISR_CONFORMANCE
    )
    assumptions = "\n".join(contract.declared_assumptions)
    assert "gate calibration" in assumptions
    assert "abstraction" in assumptions
    assert "never blurred" in assumptions


def test_matrix_identity_unchanged(engineering_rig):
    """Phase 32 measures; it does not move the capability matrix."""
    rig = engineering_rig
    assert rig.base.matrix_summary() == (12, 18, 0, 0)


# -- the evolutionary quality loop ---------------------------------------------------


def test_loop_discovers_better_architecture(engineering_rig):
    """The loop mutates ONLY the ISR (declared operators), recompiles,
    re-certifies, and reaches CERTIFIED from a QUALIFIED_PARTIAL start in
    two declared mutations — every generation chain-anchored."""
    rig = engineering_rig
    loop = rig.loop()
    result = loop.evolve_for_quality(rig.minimal_isr(), max_generations=5)
    assert result.generation <= 5
    assert result.improved is True
    assert result.certificate.verdict is EngineeringVerdict.CERTIFIED
    initial = result.lineage[0][1]
    assert initial.verdict is EngineeringVerdict.QUALIFIED_PARTIAL
    assert [cert.generation_id for _, cert in result.lineage] == [
        f"gen-{g}" for g, _ in result.lineage
    ]
    for generation, certificate in result.lineage:
        assert certificate.generation_id == f"gen-{generation}"
        assert certificate.certificate_event_ref
        assert rig.ledger.event_by_ref(certificate.certificate_event_ref) is not None
    assert rig.ledger.verify_event_chain() is True


def test_loop_never_invents_remediation(engineering_rig):
    """Weaknesses without a declared mutation mapping (e.g. a backend's
    declared-unsupported semantics) are carried, never papered over: the
    loop diagnoses them with mutation_kind None and does not act."""
    rig = engineering_rig
    certificate = rig.certify(rig.fastapi_artifact())
    weaknesses = rig.loop()._diagnose(certificate)
    assert weaknesses
    conformance_weaknesses = [
        weakness
        for weakness in weaknesses
        if weakness.dimension is EngineeringDimension.ISR_CONFORMANCE
    ]
    assert conformance_weaknesses
    assert all(
        weakness.mutation_kind is None
        for weakness in conformance_weaknesses
    )