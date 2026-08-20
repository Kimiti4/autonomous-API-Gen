"""R2.10.32.2 — Decision Traceability: the realization-chain walker.

The proof-half of the 32.1/32.2 pairing. Given an obligation ALREADY
PRESENT in the ISR, the engine demonstrates its realization through the
generated artifact by walking Requirement → Decision → Architecture →
Module/Boundary → Implementation → Verification → Evidence — resolving
existing edges (the 32.1 decision's requirement_refs / invariant_refs /
architectural_scope / verification_refs, E's member refs, the artifact's
manifest/bundle realization, the ledger's chain-anchored events) and
never authoring any of them. The acceptance surface:

    * the engine traces an ISR obligation to a five-state verdict with
      obligation_origin == "ISR";
    * the engine REFUSES any obligation that does not originate in the ISR
      (CERTIFICATION_TRACEABILITY_NEVER_CREATES_OBLIGATIONS);
    * all five states are distinguishable (SATISFIED / UNSATISFIED /
      MISSING_LINK / INVALID_REFERENCE / INSUFFICIENT_EVIDENCE);
    * INSUFFICIENT_EVIDENCE is advisory, never a pass (the vacuity policy
      applied to the certification's own chains);
    * the satisfied chain is complete (every CHAIN link kind, every link
      resolved);
    * the engine has no obligation/decision construction surface
      (structural);
    * trace evidence is chain-addressable on the ledger;
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import ast
import inspect

import pytest

from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    BusinessCapability,
    Entity,
    Module,
    Requirement,
    TestingAnchor as AnchorDeclaration,
    Workflow,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.decision import (
    ArchitecturalDecision,
)
from tiannara.application.compilation.consumption_contract import (
    CompilationTarget,
)
from tiannara.application.compilation.reference_backend import (
    ReferenceCompilerBackend,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.quality.decision_traceability import (
    DecisionTraceabilityEngine,
    ObligationOriginError,
    TraceabilityState,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _build_isr(
    *,
    decision_invariant_refs=("BND-001",),
    extra_requirements=(),
) -> ISR:
    """The trace ISR: one obligation (REQ-001) served by one decision
    (DEC-001) honoring one boundary (BND-001) over one module (MOD-A) with
    one verification anchor (ANCHOR-001) — the full realization chain, all
    edges existing."""
    module = Module(
        id="MOD-A",
        name="MOD-A",
        entities=(Entity(id="e1", name="e1"),),
        workflows=(Workflow(id="wf-1", name="wf-1"),),
    )
    capability = BusinessCapability(
        capability_id="CAP-001",
        intent="settlement ordering across contexts",
    )
    requirement = Requirement(
        requirement_id="REQ-001",
        statement="settlement must be applied in authorization order",
        target_refs=("CAP-001",),
    )
    boundary = ArchitecturalBoundary(
        boundary_id="BND-001",
        member_refs=("MOD-A",),
    )
    anchor = AnchorDeclaration(
        anchor_id="ANCHOR-001",
        subject_refs=("wf-1",),
    )
    decision = ArchitecturalDecision(
        decision_id="DEC-001",
        context="the system must guarantee settlement ordering",
        question="how should cross-context ordering be guaranteed",
        selected_strategy="a durable ordering record",
        alternatives=("a durable ordering record", "synchronous coupling"),
        trade_offs=("synchronous coupling trades availability",),
        benefits=(),
        risks=(),
        rejected={},
        future_evolution=(),
        requirement_refs=("REQ-001",),
        invariant_refs=decision_invariant_refs,
        architectural_scope=("MOD-A",),
        verification_refs=("ANCHOR-001",),
    )
    return ISR(
        system=System(
            id="trace-sys",
            name="TraceSystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,) + tuple(extra_requirements),
            architectural_boundaries=(boundary,),
            testing_anchors=(anchor,),
            architectural_decisions=(decision,),
        )
    )


class TraceRig:
    """The 32.2 machinery behind a fresh in-memory ledger (state tests must
    never observe another test's recorded evidence)."""

    def __init__(self) -> None:
        self.ledger = EvolutionLedger()
        self.engine = DecisionTraceabilityEngine()
        self.reference = ReferenceCompilerBackend(
            backend_id="trace-ref",
            backend_version="32.2.0",
            artifact_style="manifest",
        )
        self.target = CompilationTarget(
            target_id="trace-target",
            language="reference",
            runtime="reference",
            framework="reference",
        )
        self.target_b = CompilationTarget(
            target_id="trace-target-b",
            language="reference",
            runtime="reference",
            framework="reference",
        )
        self.isr = _build_isr()
        self.unreferenced_isr = _build_isr(
            extra_requirements=(
                Requirement(
                    requirement_id="REQ-002",
                    statement="an obligation no decision serves",
                    target_refs=("CAP-001",),
                ),
            )
        )
        self.dangling_isr = _build_isr(decision_invariant_refs=("BND-X",))

    def result(self, isr=None, target=None):
        return self.reference.compile(
            isr or self.isr, target or self.target
        )

    def artifact(self, *, realized=True, provenance=True, target=None):
        result = self.result(target=target)
        artifact = dict(result.artifact)
        if not realized:
            artifact["manifest"] = {"modules": [{"id": "MOD-X", "name": "MOD-X"}]}
        if provenance:
            artifact["provenance"] = {
                "artifact_hash": result.artifact_hash,
                "backend_id": result.backend_id,
            }
        return artifact

    def satisfied_trace(self):
        """The full chain realized AND evidenced: compile, record the
        compilation + verification events, then trace against the ledger."""
        result = self.result()
        self.ledger.record_compilation(result)
        self.ledger.record_verification(
            artifact_hash=result.artifact_hash, verified=True
        )
        artifact = dict(result.artifact)
        artifact["provenance"] = {
            "artifact_hash": result.artifact_hash,
            "backend_id": result.backend_id,
        }
        return self.engine.trace("REQ-001", self.isr, artifact, ledger=self.ledger)

    def state_of(self, name) -> TraceabilityState:
        if name == "satisfied_obligation":
            return self.satisfied_trace().state
        if name == "unrealized_obligation":
            return self.engine.trace(
                "REQ-001", self.isr,
                self.artifact(realized=False),
                ledger=self.ledger,
            ).state
        if name == "missing_link_obligation":
            return self.engine.trace(
                "REQ-002", self.unreferenced_isr,
                self.artifact(target=self.target),
                ledger=self.ledger,
            ).state
        if name == "dangling_ref_obligation":
            return self.engine.trace(
                "REQ-001", self.dangling_isr,
                self.artifact(target=self.target),
                ledger=self.ledger,
            ).state
        if name == "unevidenced_obligation":
            # a different artifact (different artifact_hash) than the one
            # the satisfied test recorded — realized but unrecorded.
            return self.engine.trace(
                "REQ-001", self.isr,
                self.artifact(target=self.target_b),
                ledger=self.ledger,
            ).state
        raise KeyError(name)


@pytest.fixture(scope="module")
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


@pytest.fixture
def trace_rig() -> TraceRig:
    return TraceRig()


# -- the engine traces ISR obligations ------------------------------------------


def test_engine_traces_an_isr_obligation(trace_rig):
    trace = trace_rig.satisfied_trace()
    assert trace.obligation_origin == "ISR"
    assert trace.state is TraceabilityState.SATISFIED


def test_engine_refuses_to_trace_a_non_isr_obligation(trace_rig):
    """The load-bearing invariant: the engine raises rather than constructs."""
    with pytest.raises(ObligationOriginError):
        trace_rig.engine.trace(
            "obligation_not_in_isr", trace_rig.isr, trace_rig.artifact()
        )


def test_engine_accepts_phase_32_obligation_ids(trace_rig):
    """Both id forms resolve: the Phase 32 'kind:id' form and the bare id."""
    result = trace_rig.result()
    artifact = dict(result.artifact)
    artifact["provenance"] = {
        "artifact_hash": result.artifact_hash,
        "backend_id": result.backend_id,
    }
    trace = trace_rig.engine.trace(
        "requirement:REQ-001", trace_rig.isr, artifact
    )
    assert trace.obligation_origin == "ISR"
    assert trace.obligation_id == "requirement:REQ-001"


# -- the five states -------------------------------------------------------------


def test_five_states_are_distinguishable(trace_rig):
    assert trace_rig.state_of("satisfied_obligation") is TraceabilityState.SATISFIED
    assert trace_rig.state_of("unrealized_obligation") is TraceabilityState.UNSATISFIED
    assert trace_rig.state_of("missing_link_obligation") is TraceabilityState.MISSING_LINK
    assert trace_rig.state_of("dangling_ref_obligation") is TraceabilityState.INVALID_REFERENCE
    assert trace_rig.state_of("unevidenced_obligation") is TraceabilityState.INSUFFICIENT_EVIDENCE


def test_insufficient_evidence_is_advisory_never_pass(trace_rig):
    """Vacuity policy: realized-but-unproven is named, not counted as
    satisfied and not silently counted as failed."""
    trace = trace_rig.engine.trace(
        "REQ-001", trace_rig.isr,
        trace_rig.artifact(target=trace_rig.target_b),
        ledger=trace_rig.ledger,
    )
    assert trace.state is TraceabilityState.INSUFFICIENT_EVIDENCE
    assert trace.state is not TraceabilityState.SATISFIED


def test_unrealized_obligation_is_not_satisfied(trace_rig):
    """An obligation whose module is not carried by the artifact is
    UNSATISFIED, never a silent pass."""
    trace = trace_rig.engine.trace(
        "REQ-001", trace_rig.isr, trace_rig.artifact(realized=False)
    )
    assert trace.state is TraceabilityState.UNSATISFIED


# -- the chain -------------------------------------------------------------------


def test_chain_is_complete_for_satisfied(trace_rig):
    trace = trace_rig.satisfied_trace()
    assert {l.link_kind for l in trace.links} == set(DecisionTraceabilityEngine.CHAIN)
    assert all(l.resolved for l in trace.links)


def test_each_link_kind_is_walked_in_order(trace_rig):
    trace = trace_rig.satisfied_trace()
    assert [l.link_kind for l in trace.links] == list(DecisionTraceabilityEngine.CHAIN)
    # the walk follows existing edges: REQ-001 -> DEC-001 -> BND-001 ->
    # MOD-A -> ANCHOR-001 -> verification event.
    assert trace.links[0].to_ref == "DEC-001"
    assert trace.links[1].to_ref == "BND-001"
    assert trace.links[2].to_ref == "MOD-A"
    assert trace.links[4].to_ref == "ANCHOR-001"


def test_engine_has_no_obligation_creation_surface(trace_rig):
    """Structural: the engine cannot construct obligations or decisions."""
    tree = ast.parse(inspect.getsource(DecisionTraceabilityEngine))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "ArchitecturalDecision(" not in fn
            assert "create_obligation" not in fn and "add_obligation" not in fn


def test_trace_evidence_is_chain_addressable(trace_rig):
    trace = trace_rig.satisfied_trace()
    assert trace.evidence_refs
    for ref in trace.evidence_refs:
        assert trace_rig.ledger.event_by_ref(ref) is not None


def test_missing_evidence_is_not_chain_addressable(trace_rig):
    trace = trace_rig.engine.trace(
        "REQ-001", trace_rig.isr,
        trace_rig.artifact(target=trace_rig.target_b),
        ledger=trace_rig.ledger,
    )
    assert trace.state is TraceabilityState.INSUFFICIENT_EVIDENCE
    assert trace.evidence_refs == ()


# -- identity stability -----------------------------------------------------------


def test_matrix_and_recipe_identity_unchanged(campaign_harness):
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH
    assert campaign_harness.matrix_summary() == (12, 18, 0, 0)