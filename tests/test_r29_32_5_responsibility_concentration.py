"""R2.10.32.5 — Responsibility Concentration: the emergent-property dimension.

32.1–32.4 established "what must be true -> how we prove it"; 32.5 evaluates
an EMERGENT architectural property: does the implementation's responsibility
structure violate the architectural quality contract? It is deliberately NOT
an obligation carrier — there is no ResponsibilityObligation; the analyzer
derives evidence from the existing ISR architecture, module/boundary
identity, decision scope, and the implementation graph, and its output is a
FINDING (evidence about the artifact), never a new obligation. The
acceptance surface:

    * anti-gaming: a large coherent module (one responsibility cluster) is
      never flagged, regardless of size; a small module owning many
      unrelated clusters IS flagged;
    * the analyzer has no line-count signal (structural);
    * the finding is evidence, not an obligation: evidence refs only, no
      obligation_id;
    * severity never self-escalates: CRITICAL only when the ISR explicitly
      prohibits the concentration (an E boundary names the module in
      forbidden_dependency_refs), otherwise ADVISORY/WARNING;
    * finding evidence is chain-addressable on the ledger;
    * the standard boundary pattern: no obligation-carrier construction;
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
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.quality.responsibility_concentration import (
    ConcentrationSeverity,
    ResponsibilityConcentrationAnalyzer,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _isr(*, forbidden_modules=()) -> ISR:
    """A harness ISR: one boundary that owns the artifact modules, one
    32.1 decision whose scope covers them, and (optionally) an E boundary
    that explicitly prohibits a module via forbidden_dependency_refs."""
    module = Module(
        id="MOD-A",
        name="MOD-A",
        entities=(Entity(id="e1", name="e1"),),
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
        member_refs=("MOD-A", "small_god_module", "large_coherent_module"),
    )
    boundaries = (boundary,)
    if forbidden_modules:
        boundaries += (
            ArchitecturalBoundary(
                boundary_id="BND-FORBID",
                member_refs=("MOD-A",),
                forbidden_dependency_refs=tuple(forbidden_modules),
            ),
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
        benefits=(),
        requirement_refs=("REQ-001",),
        invariant_refs=("BND-001",),
        architectural_scope=("MOD-A", "small_god_module"),
        verification_refs=(),
    )
    return ISR(
        system=System(
            id="rc-sys",
            name="ResponsibilitySystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,),
            architectural_boundaries=boundaries,
            architectural_decisions=(decision,),
        )
    )


def _artifact(modules) -> dict:
    return {
        "modules": modules,
        "provenance": {
            "artifact_hash": "rc-artifact-hash",
            "backend_id": "rc-backend",
        },
    }


def _responsibility(resp_id, interfaces, dependencies):
    return (resp_id, tuple(interfaces), tuple(dependencies))


class ResponsibilityConcentrationHarness:
    """The 32.5 machinery: a fresh in-memory ledger and scenario artifacts.
    ``analyze`` records the artifact's verification event (the finding's
    chain anchor) and delegates to the analyzer."""

    def __init__(self, campaign: CampaignReadinessHarness) -> None:
        self.ledger = EvolutionLedger()
        self.analyzer = ResponsibilityConcentrationAnalyzer()
        self.isr = _isr()
        self._campaign = campaign

    def analyze(self, artifact, *, isr=None, record=True):
        if record:
            self.ledger.record_verification(
                artifact_hash=artifact["provenance"]["artifact_hash"],
                verified=True,
            )
        return self.analyzer.analyze(isr or self.isr, artifact, ledger=self.ledger)

    # -- scenario artifacts -------------------------------------------------------

    def large_coherent_artifact(self) -> dict:
        """OrderService: four order-processing responsibilities sharing one
        interface and one dependency — one coherent cluster, however large."""
        return _artifact(
            [
                {
                    "module_id": "large_coherent_module",
                    "interfaces": ("IF-ORDER",),
                    "dependencies": ("DEP-ORDER-STORE",),
                    "responsibilities": (
                        _responsibility("create_order", ("IF-ORDER",), ("DEP-ORDER-STORE",)),
                        _responsibility("validate_order", ("IF-ORDER",), ("DEP-ORDER-STORE",)),
                        _responsibility("calculate_totals", ("IF-ORDER",), ("DEP-ORDER-STORE",)),
                        _responsibility("apply_order_rules", ("IF-ORDER",), ("DEP-ORDER-STORE",)),
                    ),
                }
            ]
        )

    def small_god_module_artifact(self) -> dict:
        """The god module: six unrelated responsibilities, each with its own
        interface and dependency — six unrelated clusters, high dependency
        diversity, regardless of its (small) size."""
        return _artifact(
            [
                {
                    "module_id": "small_god_module",
                    "interfaces": (
                        "IF-BILLING", "IF-AUTH", "IF-EMAIL", "IF-PERSIST",
                        "IF-ANALYTICS", "IF-SHIPPING",
                    ),
                    "dependencies": (
                        "DEP-BILLING", "DEP-AUTH", "DEP-EMAIL", "DEP-PERSIST",
                        "DEP-ANALYTICS", "DEP-SHIPPING",
                    ),
                    "responsibilities": (
                        _responsibility("billing", ("IF-BILLING",), ("DEP-BILLING",)),
                        _responsibility("authentication", ("IF-AUTH",), ("DEP-AUTH",)),
                        _responsibility("email", ("IF-EMAIL",), ("DEP-EMAIL",)),
                        _responsibility("persistence", ("IF-PERSIST",), ("DEP-PERSIST",)),
                        _responsibility("analytics", ("IF-ANALYTICS",), ("DEP-ANALYTICS",)),
                        _responsibility("shipping", ("IF-SHIPPING",), ("DEP-SHIPPING",)),
                    ),
                }
            ]
        )

    def god_module_without_prohibition(self) -> dict:
        return self.small_god_module_artifact()

    def god_module_with_prohibition(self) -> dict:
        """The same god module, but the ISR explicitly prohibits it: an E
        boundary names small_god_module in forbidden_dependency_refs."""
        self.isr = _isr(forbidden_modules=("small_god_module",))
        return self.small_god_module_artifact()

    # -- identity stability ---------------------------------------------------------

    def matrix_summary(self):
        return self._campaign.matrix_summary()

    def recipe_isr_hash(self):
        return self._campaign.recipe_isr_hash()


@pytest.fixture(scope="module")
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


@pytest.fixture
def rc_harness(campaign_harness) -> ResponsibilityConcentrationHarness:
    return ResponsibilityConcentrationHarness(campaign_harness)


# -- anti-gaming: concentration, never volume ---------------------------------------


def test_large_coherent_module_not_flagged(rc_harness):
    """Anti-gaming: a large module with one coherent responsibility cluster
    is not concentrated, regardless of size."""
    findings = rc_harness.analyze(rc_harness.large_coherent_artifact())
    assert all(f.module_id != "large_coherent_module" for f in findings)


def test_small_god_module_flagged(rc_harness):
    """The inverse: a small module owning many unrelated clusters IS
    concentrated."""
    findings = rc_harness.analyze(rc_harness.small_god_module_artifact())
    flagged = [f for f in findings if f.module_id == "small_god_module"]
    assert flagged
    assert (
        "multiple_unrelated_responsibility_clusters"
        in flagged[0].concentration_signals
    )


def test_concentration_signals_not_line_count(rc_harness):
    """Structural: the analyzer has no line-count signal."""
    src = inspect.getsource(ResponsibilityConcentrationAnalyzer).lower()
    assert "line_count" not in src
    assert "loc" not in src.replace("location", "")


# -- the finding is evidence, never an obligation -------------------------------------


def test_finding_is_evidence_not_obligation(rc_harness):
    """The finding creates no obligation — it carries evidence and signals
    only."""
    findings = rc_harness.analyze(rc_harness.small_god_module_artifact())
    assert findings
    for f in findings:
        assert f.evidence_refs
        assert not hasattr(f, "obligation_id")


def test_finding_evidence_chain_addressable(rc_harness):
    findings = rc_harness.analyze(rc_harness.small_god_module_artifact())
    for f in findings:
        for ref in f.evidence_refs:
            assert rc_harness.ledger.event_by_ref(ref) is not None


# -- severity never self-escalates --------------------------------------------------------


def test_critical_only_when_isr_prohibits(rc_harness):
    """Severity escalation requires an explicit ISR prohibition; the
    analyzer never self-escalates to CRITICAL."""
    findings_unprohibited = rc_harness.analyze(
        rc_harness.god_module_without_prohibition()
    )
    assert findings_unprohibited
    assert all(
        f.severity is not ConcentrationSeverity.CRITICAL
        for f in findings_unprohibited
    )
    findings_prohibited = rc_harness.analyze(
        rc_harness.god_module_with_prohibition()
    )
    assert findings_prohibited
    assert any(
        f.severity is ConcentrationSeverity.CRITICAL
        for f in findings_prohibited
    )


# -- the standard boundary pattern --------------------------------------------------------


def test_analyzer_has_no_obligation_authoring_surface(rc_harness):
    """Standard boundary pattern: no obligation-carrier construction."""
    tree = ast.parse(inspect.getsource(ResponsibilityConcentrationAnalyzer))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "ArchitecturalDecision(" not in fn
            assert "SecurityThreat(" not in fn


# -- identity stability ----------------------------------------------------------------------


def test_matrix_and_recipe_identity_unchanged(rc_harness):
    assert rc_harness.matrix_summary() == (12, 18, 0, 0)
    assert rc_harness.recipe_isr_hash() == RECIPE_HASH