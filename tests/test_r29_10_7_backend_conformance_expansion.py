"""R2.10.7 expansion — conformance of the remaining six real backends.

R2.10.7 proved the frozen contract against FastAPI, the first-fail
candidate. This suite expands the conformance campaign to the remaining six
real backends (react, postgres, terraform, cicd, pytest, markdown), each
carrying an explicit, source-verified capability declaration. The
acceptance evidence:

  1.  every declaration covers all twelve semantics — no silent gaps in the
      map itself;
  2.  UNSUPPORTED is the default, never omission: a semantic not declared
      is UNSUPPORTED;
  3.  each of the six backends produces a conformance report on which all
      eight gates hold — a failure is recorded, never papered over;
  4.  Gate D across every backend: nothing silently omitted (the declared
      coverage covers every expressed carrier);
  5.  the ISR stays technology-neutral across all six real compilations;
  6.  the milestone: the cross-backend campaign proves ONE invariant
      semantic source across all SEVEN divergent realizations;
  7.  every conformance report is chain-anchored in the evidence ledger;
  8.  the seams deliver real content (react views from workflows, postgres
      DDL from migration targets) — the coverage is not hollow;
  9.  Option A (fifteenth use) — no new carriers, no matrix movement.
"""
from __future__ import annotations

import tempfile

import pytest

from constitutional_architecture.isr.semantics.projection import (
    semantic_content_hash,
)
from tiannara.application.compilation.backend_capability_registry import (
    BACKEND_DECLARATIONS,
    SEMANTIC_IDS,
    BackendRegistry,
    conform_all_backends,
    declaration,
)
from tiannara.application.compilation.backend_conformance import (
    BackendConformanceEvaluator,
    CapabilitySupport,
)
from tiannara.application.compilation.consumption_contract import (
    ContaminationGuard,
    enumerate_isr_semantics,
)
from tiannara.application.compilation.cross_backend_campaign import (
    CrossBackendConformanceCampaign,
)
from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_4_semantic_evolution_gate import (
    SemanticEvolutionIntegrationHarness,
)

SIX = ("react", "postgres", "terraform", "cicd", "pytest", "markdown")
SEVEN = SIX + ("fastapi",)


class ExpansionHarness:
    """The six + FastAPI registry wired to the frozen gate + evaluator."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = CompilationIntegrityGate(ledger=self.ledger)
        self.guard = ContaminationGuard()
        self.evaluator = BackendConformanceEvaluator(
            integrity_gate=self.gate,
            contamination_guard=self.guard,
            ledger=self.ledger,
        )
        self.registry = BackendRegistry()
        self._base = SemanticEvolutionIntegrationHarness()

    def fixed_isr(self):
        return self._base.parent_isr()

    def adapter(self, backend_id: str):
        return self.registry.adapter(backend_id)

    def target(self, backend_id: str):
        return self.registry.target(backend_id)

    def all_seven_adapters(self) -> dict:
        return {
            backend_id: self.registry.adapter(backend_id)
            for backend_id in SEVEN
        }

    def targets(self) -> dict:
        return {
            backend_id: self.registry.target(backend_id)
            for backend_id in SEVEN
        }

    def matrix_summary(self):
        from tiannara.application.evolution.isr_capability_audit import (
            ISRCapabilityAudit,
        )

        result = ISRCapabilityAudit().run(RECIPE)
        summary = result.summary()
        return (summary["expressed"], summary["partial"], summary["missing"])

    def recipe_isr_hash(self):
        return RECIPE.content_hash


@pytest.fixture
def expansion_harness() -> ExpansionHarness:
    return ExpansionHarness()


# =============================================================================
# 1.  Every declaration covers all twelve semantics
# =============================================================================

def test_every_declaration_covers_all_semantics():
    """The map itself has no silent gaps: each declaration is exactly the
    twelve semantic ids, each with an explicit verdict."""
    for backend_id, decl in BACKEND_DECLARATIONS.items():
        assert set(decl.declarations) == set(SEMANTIC_IDS), (
            f"{backend_id} declaration incomplete"
        )


# =============================================================================
# 2.  UNSUPPORTED is the default, never omission
# =============================================================================

def test_undeclared_semantic_is_unsupported():
    decl = declaration("probe", supported={"documentation"}, partial=set())
    assert decl.support_for("data_migrations") is CapabilitySupport.UNSUPPORTED
    assert decl.support_for("documentation") is CapabilitySupport.SUPPORTED


# =============================================================================
# 3.  Each of the six backends produces a conformance report (all gates hold)
# =============================================================================

def test_each_backend_produces_a_conformance_report(expansion_harness):
    """Every registered backend is conformed and reports; a failure must be
    recorded — never silent — and here the milestone demands green: all
    eight gates hold for each of the six."""
    reports = conform_all_backends(
        expansion_harness.fixed_isr(),
        expansion_harness.registry,
        expansion_harness.evaluator,
    )
    assert set(reports) == set(SIX) | {"fastapi"}
    for backend_id, report in reports.items():
        assert report.conforms is True, (
            f"{backend_id}: failed gates {report.failed_gates}"
        )
        assert report.failed_gates == ()


# =============================================================================
# 4.  Gate D across every backend: nothing silently omitted
# =============================================================================

def test_no_silent_omission_across_six(expansion_harness):
    """The declared coverage covers every carrier the fixed ISR expresses —
    for each of the six backends, through the 12->14 expansion."""
    isr = expansion_harness.fixed_isr()
    required = set(enumerate_isr_semantics(isr))
    for backend_id in SIX:
        adapter = expansion_harness.adapter(backend_id)
        result = adapter.compile(isr, expansion_harness.target(backend_id))
        covered = {c.capability_id for c in result.capability_coverage}
        assert required <= covered, (
            f"{backend_id} silently omits {sorted(required - covered)}"
        )


# =============================================================================
# 5.  The ISR stays technology-neutral across all six compilations
# =============================================================================

def test_isr_neutral_across_six(expansion_harness):
    """The six real compilations consume the projection, never the ISR: the
    semantic content is byte-identical before and after."""
    isr = expansion_harness.fixed_isr()
    before = semantic_content_hash(isr)
    expansion_harness.guard.assert_isr_technology_neutral(isr)
    for backend_id in SIX:
        expansion_harness.adapter(backend_id).compile(
            isr, expansion_harness.target(backend_id)
        )
    expansion_harness.guard.assert_isr_technology_neutral(isr)
    assert semantic_content_hash(isr) == before


# =============================================================================
# 6.  The milestone: semantic invariance across ALL SEVEN backends
# =============================================================================

def test_cross_backend_semantic_invariance(expansion_harness):
    """One fixed ISR through all seven realizations: ONE invariant semantic
    source, divergent artifacts, every backend conforming."""
    isr = expansion_harness.fixed_isr()
    campaign = CrossBackendConformanceCampaign()
    report = campaign.run(
        isr,
        expansion_harness.all_seven_adapters(),
        expansion_harness.evaluator,
        expansion_harness.targets(),
    )
    assert report.semantic_invariance_held is True
    assert report.artifact_divergence_count > 1
    assert set(report.per_backend) == set(SEVEN)
    assert report.all_conform is True


# =============================================================================
# 7.  Every report enters the evidence chain
# =============================================================================

def test_conformance_reports_chain_anchored(expansion_harness):
    """Seven CERTIFICATION events, each binding backend + verdict + ISR
    hash, on a verifying chain."""
    conform_all_backends(
        expansion_harness.fixed_isr(),
        expansion_harness.registry,
        expansion_harness.evaluator,
    )
    certifications = [
        ev
        for ev in expansion_harness.ledger._events
        if ev.event_type is EventType.CERTIFICATION
    ]
    assert len(certifications) == len(SEVEN)
    backend_ids = {ev.payload["backend_id"] for ev in certifications}
    assert backend_ids == set(SEVEN)
    assert all(ev.payload["conforms"] for ev in certifications)
    assert expansion_harness.ledger.verify_event_chain() is True


# =============================================================================
# 8.  The seams deliver real content (coverage is not hollow)
# =============================================================================

def test_react_views_and_components_derive_from_projection(expansion_harness):
    """The react artifact routes a page per workflow and a component per
    capability — the seam's translation is real content, not empty files."""
    adapter = expansion_harness.adapter("react")
    result = adapter.compile(
        expansion_harness.fixed_isr(), expansion_harness.target("react")
    )
    bundle = result.artifact["bundle"]
    files = bundle["manifests"][0]["files"]
    assert any("W1Page" in path for path in files)
    assert any("Capability_PayPage" in path for path in files)


def test_postgres_ddl_derives_from_migration_targets(expansion_harness):
    """The postgres DDL realizes the migration's target schema — the
    projection delivers the data surface the backend actually consumes."""
    adapter = expansion_harness.adapter("postgres")
    result = adapter.compile(
        expansion_harness.fixed_isr(), expansion_harness.target("postgres")
    )
    files = result.artifact["bundle"]["manifests"][0]["files"]
    ddl = files["schema.sql"]
    assert "CREATE TABLE e2 (" in ddl


def test_cicd_pipeline_derives_from_carrier_presence(expansion_harness):
    """The meta-compiler's pipeline realizes the stages the projection's
    carriers make present: a test stage (testing anchors) and a deployment
    stage (deployment intent)."""
    adapter = expansion_harness.adapter("cicd")
    result = adapter.compile(
        expansion_harness.fixed_isr(), expansion_harness.target("cicd")
    )
    files = result.artifact["bundle"]["manifests"][0]["files"]
    workflow = files[".github/workflows/deploy.yml"]
    assert "Run compiled test suite" in workflow
    assert "Provision infrastructure" in workflow


# =============================================================================
# 9.  Option A (fifteenth use) — no new carriers, no matrix movement
# =============================================================================

def test_expansion_moves_no_matrix_row(expansion_harness):
    assert expansion_harness.matrix_summary() == (12, 18, 0)
    assert (
        expansion_harness.recipe_isr_hash()
        == "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
    )