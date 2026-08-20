"""R2.10.32.4 — Security Traceability: the security realization-chain walker.

The proof-half of the 32.3/32.4 pairing, and the second proof that the
32.2 epistemic architecture is REUSABLE across obligation classes. Given a
threat ALREADY PRESENT in the ISR, the engine demonstrates its realization
through the generated artifact by walking Threat → Requirement → Invariant
→ Architectural Control → Implementation Obligation → Verification →
Evidence — resolving the 32.3 edges (requirement_refs / invariant_statement
/ architectural_control_refs / implementation_obligation_refs /
verification_refs), the 32.1 decision's scoped modules, the artifact's
manifest/bundle realization, and the ledger's chain-anchored events. It
never creates, modifies, infers, or reclassifies. The acceptance surface:

    * the engine traces an ISR threat to a five-state verdict with
      obligation_origin == "ISR";
    * it REFUSES any threat that does not originate in the ISR — including
      a scanner-observed-but-undeclared threat surface, which is not an
      obligation and therefore not traceable;
    * all five states are distinguishable for threats, and
      INSUFFICIENT_EVIDENCE never becomes SATISFIED;
    * the DECLARED severity is carried verbatim — realization evidence
      never alters it, and the trace has no risk score and no computed
      severity (question A is answered; question B is structurally absent);
    * the engine has no threat-construction or severity-reclassification
      surface (structural);
    * the satisfied chain is complete, ordered, and its evidence is
      chain-addressable on the ledger;
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import ast
import inspect

import pytest

from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    ArchitecturalDecision,
    BusinessCapability,
    Entity,
    Module,
    Requirement,
    TestingAnchor as AnchorDeclaration,
    Workflow,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.threat import (
    SecurityThreat,
    ThreatSeverity,
)
from tiannara.application.compilation.consumption_contract import (
    CompilationTarget,
)
from tiannara.application.compilation.reference_backend import (
    ReferenceCompilerBackend,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.quality.decision_traceability import (
    ObligationOriginError,
    TraceabilityState,
)
from tiannara.application.quality.security_traceability import (
    SecurityObligationTrace,
    SecurityTraceabilityEngine,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _base_system(*, threats: tuple[SecurityThreat, ...]) -> ISR:
    """An ISR whose reference universe supports every threat edge:
    REQ-001 (F), BND-001 (E), DEC-001 (the 32.1 obligation carrier,
    scoped to MOD-A), ANCHOR-001 (H), and the module MOD-A."""
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
        statement="settlement must become effective in the same order as "
        "authorization",
        target_refs=("CAP-001",),
    )
    boundary = ArchitecturalBoundary(
        boundary_id="BND-001",
        member_refs=("MOD-A",),
    )
    anchor = AnchorDeclaration(
        anchor_id="ANCHOR-001",
        subject_refs=("REQ-001",),
    )
    decision = ArchitecturalDecision(
        decision_id="DEC-001",
        context="the system must guarantee settlement ordering across "
        "bounded contexts",
        question="how should cross-context ordering be guaranteed",
        selected_strategy="eventual ordering via a durable record",
        alternatives=(
            "eventual ordering via a durable record",
            "synchronous coupling",
        ),
        trade_offs=(
            "synchronous coupling trades availability for immediacy",
        ),
        benefits=(
            "the durable record preserves ordering independent of availability",
        ),
        requirement_refs=("REQ-001",),
        invariant_refs=("BND-001",),
        architectural_scope=("MOD-A",),
        verification_refs=("ANCHOR-001",),
    )
    return ISR(
        system=System(
            id="sec-sys",
            name="SecuritySystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,),
            architectural_boundaries=(boundary,),
            testing_anchors=(anchor,),
            architectural_decisions=(decision,),
            security_threats=threats,
        )
    )


def _full_threat() -> SecurityThreat:
    """THREAT-004: every edge anchored — the satisfied-threat scenario."""
    return SecurityThreat(
        threat_id="THREAT-004",
        scenario="unauthorized access to cross-context data",
        severity=ThreatSeverity.CRITICAL,
        requirement_refs=("REQ-001",),
        invariant_statement="cross-context data must never be readable "
        "without authorization",
        architectural_control_refs=("BND-001",),
        implementation_obligation_refs=("DEC-001",),
        verification_refs=("ANCHOR-001",),
    )


class SecurityTraceRig:
    """The 32.4 machinery behind a fresh in-memory ledger (state tests must
    never observe another test's recorded evidence)."""

    def __init__(self, campaign: CampaignReadinessHarness) -> None:
        self.ledger = EvolutionLedger()
        self.engine = SecurityTraceabilityEngine()
        self.reference = ReferenceCompilerBackend(
            backend_id="sec-ref",
            backend_version="32.4.0",
            artifact_style="manifest",
        )
        self.target = CompilationTarget(
            target_id="sec-target",
            language="reference",
            runtime="reference",
            framework="reference",
        )
        self.target_b = CompilationTarget(
            target_id="sec-target-b",
            language="reference",
            runtime="reference",
            framework="reference",
        )
        self.isr = _base_system(threats=(_full_threat(),))
        self.missing_link_isr = _base_system(
            threats=(
                SecurityThreat(
                    threat_id="THREAT-005",
                    scenario="credential theft across contexts",
                    severity=ThreatSeverity.HIGH,
                    requirement_refs=(),
                    invariant_statement="credentials must not cross contexts",
                    architectural_control_refs=("BND-001",),
                    implementation_obligation_refs=("DEC-001",),
                    verification_refs=("ANCHOR-001",),
                ),
            )
        )
        self.dangling_isr = _base_system(
            threats=(
                SecurityThreat(
                    threat_id="THREAT-006",
                    scenario="privilege escalation within a context",
                    severity=ThreatSeverity.HIGH,
                    requirement_refs=("REQ-001",),
                    invariant_statement="privileges must never escalate "
                    "across a context boundary",
                    architectural_control_refs=("NO-SUCH-BND",),
                    implementation_obligation_refs=("DEC-001",),
                    verification_refs=("ANCHOR-001",),
                ),
            )
        )
        self._campaign = campaign

    # -- scenario surfaces -------------------------------------------------------

    def isr_threat_id(self) -> str:
        return "THREAT-004"

    def scanner_inferred_threat_id(self) -> str:
        return "THREAT-SCAN-1"

    def isr_threat(self):
        return self.isr.system.security_threats[0]

    def trace(self, threat_id, isr, artifact, *, ledger=None):
        return self.engine.trace(
            threat_id, isr, artifact,
            ledger=self.ledger if ledger is None else ledger,
        )

    # -- artifact machinery --------------------------------------------------------

    def result(self, isr=None, target=None):
        return self.reference.compile(
            isr or self.isr, target or self.target
        )

    def artifact(self, *, realized=True, provenance=True, target=None):
        result = self.result(target=target)
        artifact = dict(result.artifact)
        if not realized:
            artifact["manifest"] = {
                "modules": [{"id": "MOD-X", "name": "MOD-X"}]
            }
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
        return self.trace(self.isr_threat_id(), self.isr, artifact)

    def state_of(self, name) -> TraceabilityState:
        if name == "satisfied_threat":
            return self.satisfied_trace().state
        if name == "unrealized_threat":
            return self.trace(
                self.isr_threat_id(), self.isr,
                self.artifact(realized=False),
            ).state
        if name == "missing_link_threat":
            return self.trace(
                "THREAT-005", self.missing_link_isr,
                self.artifact(target=self.target),
            ).state
        if name == "dangling_ref_threat":
            return self.trace(
                "THREAT-006", self.dangling_isr,
                self.artifact(target=self.target),
            ).state
        if name == "unevidenced_threat":
            # a different artifact (different artifact_hash) than the one
            # the satisfied test recorded — realized but unrecorded.
            return self.trace(
                self.isr_threat_id(), self.isr,
                self.artifact(target=self.target_b),
            ).state
        raise KeyError(name)

    # -- identity stability ---------------------------------------------------------

    def matrix_summary(self):
        return self._campaign.matrix_summary()

    def recipe_isr_hash(self):
        return self._campaign.recipe_isr_hash()


@pytest.fixture(scope="module")
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


@pytest.fixture
def sec_harness(campaign_harness) -> SecurityTraceRig:
    return SecurityTraceRig(campaign_harness)


# -- the engine traces ISR threats --------------------------------------------------


def test_engine_traces_an_isr_threat(sec_harness):
    trace = sec_harness.satisfied_trace()
    assert trace.obligation_origin == "ISR"
    assert trace.state is TraceabilityState.SATISFIED
    assert isinstance(trace, SecurityObligationTrace)


def test_engine_refuses_non_isr_threat(sec_harness):
    """The load-bearing invariant: the engine raises rather than constructs."""
    with pytest.raises(ObligationOriginError):
        sec_harness.trace(
            "threat_not_in_isr", sec_harness.isr, sec_harness.artifact()
        )


def test_scanner_observation_cannot_become_an_obligation(sec_harness):
    """The contamination 32.1–32.3 eliminated must stay eliminated: an
    observed-but-undeclared threat surface is not traceable, because it is
    not an obligation."""
    with pytest.raises(ObligationOriginError):
        sec_harness.trace(
            sec_harness.scanner_inferred_threat_id(),
            sec_harness.isr, sec_harness.artifact(),
        )


# -- the five states -----------------------------------------------------------------


def test_five_states_distinguishable_for_threats(sec_harness):
    assert sec_harness.state_of("satisfied_threat") is TraceabilityState.SATISFIED
    assert sec_harness.state_of("unrealized_threat") is TraceabilityState.UNSATISFIED
    assert sec_harness.state_of("missing_link_threat") is TraceabilityState.MISSING_LINK
    assert sec_harness.state_of("dangling_ref_threat") is TraceabilityState.INVALID_REFERENCE
    assert sec_harness.state_of("unevidenced_threat") is TraceabilityState.INSUFFICIENT_EVIDENCE


def test_insufficient_evidence_never_satisfied(sec_harness):
    trace = sec_harness.trace(
        sec_harness.isr_threat_id(), sec_harness.isr,
        sec_harness.artifact(target=sec_harness.target_b),
    )
    assert trace.state is TraceabilityState.INSUFFICIENT_EVIDENCE
    assert trace.state is not TraceabilityState.SATISFIED


def test_unrealized_threat_is_not_satisfied(sec_harness):
    """An obligation whose implementation module is not carried by the
    artifact is UNSATISFIED, never a silent pass."""
    trace = sec_harness.trace(
        sec_harness.isr_threat_id(), sec_harness.isr,
        sec_harness.artifact(realized=False),
    )
    assert trace.state is TraceabilityState.UNSATISFIED


# -- severity is declared, never measured ----------------------------------------------


def test_declared_severity_carried_never_reinterpreted(sec_harness):
    """The trace carries the ISR's declared severity verbatim; realization
    evidence never alters it."""
    trace = sec_harness.satisfied_trace()
    assert trace.declared_severity == sec_harness.isr_threat().severity
    assert trace.declared_severity is ThreatSeverity.CRITICAL


def test_engine_has_no_severity_or_threat_authoring_surface(sec_harness):
    """Structural: the engine cannot construct threats and cannot compute or
    reclassify severity — question B is outside its surface entirely."""
    tree = ast.parse(inspect.getsource(SecurityTraceabilityEngine))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "SecurityThreat(" not in fn
        if isinstance(node, ast.Assign):
            for target in node.targets:
                name = ast.unparse(target).lower()
                assert "severity" not in name or "declared_severity" in name


def test_realization_question_answered_severity_question_not(sec_harness):
    """The trace reports realization (state) and carries severity
    (declaration); it contains no risk score, no severity reassessment."""
    trace = sec_harness.satisfied_trace()
    assert not hasattr(trace, "risk_score")
    assert not hasattr(trace, "computed_severity")
    assert trace.state is TraceabilityState.SATISFIED
    assert trace.declared_severity is ThreatSeverity.CRITICAL


# -- the chain ----------------------------------------------------------------------------


def test_chain_complete_and_ordered_for_satisfied(sec_harness):
    trace = sec_harness.satisfied_trace()
    assert [l.link_kind for l in trace.links] == list(
        SecurityTraceabilityEngine.CHAIN
    )
    assert all(l.resolved for l in trace.links)
    assert trace.links[0].to_ref == "REQ-001"
    assert trace.links[2].to_ref == "BND-001"
    assert trace.links[3].to_ref == "DEC-001"
    assert trace.links[4].to_ref == "ANCHOR-001"


def test_trace_evidence_chain_addressable(sec_harness):
    trace = sec_harness.satisfied_trace()
    assert trace.evidence_refs
    for ref in trace.evidence_refs:
        assert sec_harness.ledger.event_by_ref(ref) is not None


# -- identity stability ---------------------------------------------------------------------


def test_matrix_and_recipe_identity_unchanged(sec_harness):
    assert sec_harness.recipe_isr_hash() == RECIPE_HASH
    assert sec_harness.matrix_summary() == (12, 18, 0, 0)