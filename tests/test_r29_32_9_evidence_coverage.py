"""R2.10.32.9 — Complete Evidence Coverage: the evidence-completion phase.

The acceptance surface:

    * the seven spec metrics are measured deterministically, as
      emergent-property evidence (no obligation_id on a measurement);
    * all eleven required external tools are probed honestly — absence
      is a state (TOOL_NOT_INSTALLED), never an omission;
    * a dimension with absent producers is UNPROVEN, never PROVEN
      (vacuity policy);
    * the senior-quality contract is ten gates, all-pass — no composite
      score field exists structurally;
    * every criterion carries a declared calibration basis;
    * a critical finding blocks CERTIFIED structurally;
    * the operational observability surface is evidenced;
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import dataclasses

import pytest

from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    ArchitecturalDecision,
    BusinessCapability,
    Deployment,
    DeploymentIntent,
    Entity,
    FailureMode,
    Module,
    NetworkingConfig,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    SecurityThreat,
    StorageConfig,
    ThreatSeverity,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from tiannara.application.quality.engineering_contract import (
    EngineeringVerdict,
)
from tiannara.application.quality.metric_analyzers import (
    CodeDuplicationAnalyzer,
    CyclomaticComplexityAnalyzer,
    DeadCodeAnalyzer,
    DocumentationCoverageAnalyzer,
    MetricMeasurement,
    NamingConsistencyAnalyzer,
    PublicAPIConsistencyAnalyzer,
    UnusedDependenciesAnalyzer,
)
from tiannara.application.quality.operational_evidence import (
    OperationalEvidenceAnalyzer,
)
from tiannara.application.quality.senior_quality_contract import (
    SENIOR_QUALITY_CONTRACT,
    SeniorQualityCertificationGate,
)
from tiannara.application.quality.tool_adapters import (
    AnalyzerRegistry,
    ExemplarToolAdapter,
)
from tiannara.application.quality.tool_availability import (
    REQUIRED_EXTERNAL_TOOLS,
    ToolAvailabilityProbe,
    implementation_quality_dimension_state,
)
from tiannara.application.quality.analyzer_contract import AnalyzerIdentity

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"

UNIT_MAIN = {
    "unit_id": "mod_a.py::main",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 1,
    "lines": 5,
    "docstring": True,
    "referenced_by": (),
    "body_fingerprint": "fp-main",
    "name": "main",
}
UNIT_F1 = {
    "unit_id": "mod_a.py::f1",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 5,
    "lines": 40,
    "docstring": True,
    "referenced_by": ("mod_a.py::main",),
    "body_fingerprint": "fp-1",
    "name": "process_settlement",
}
UNIT_F2 = {
    "unit_id": "mod_a.py::f2",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 2,
    "lines": 10,
    "docstring": True,
    "referenced_by": ("mod_a.py::f1",),
    "body_fingerprint": "fp-2",
    "name": "normalize_order",
}
UNIT_F3 = {
    "unit_id": "mod_a.py::f3",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 3,
    "lines": 15,
    "docstring": False,
    "referenced_by": (),
    "body_fingerprint": "fp-3",
    "name": "orphaned_helper",
}
UNIT_F4 = {
    "unit_id": "mod_a.py::f4",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 1,
    "lines": 8,
    "docstring": True,
    "referenced_by": ("mod_a.py::f1",),
    "body_fingerprint": "fp-1",
    "name": "process_settlement_duplicate",
}
UNIT_F5 = {
    "unit_id": "mod_a.py::f5",
    "module": "mod_a",
    "kind": "function",
    "decision_points": 1,
    "lines": 6,
    "docstring": True,
    "referenced_by": ("mod_a.py::f1",),
    "body_fingerprint": "fp-4",
    "name": "processSettlement",
}

ARTIFACT_UNITS = (
    UNIT_MAIN,
    UNIT_F1,
    UNIT_F2,
    UNIT_F3,
    UNIT_F4,
    UNIT_F5,
)

ARTIFACT_MODULES = (
    {
        "module_id": "mod_a",
        "public_surface": 3,
        "documented_surface": 2,
        "dependencies": ("dep_a", "dep_b"),
    },
)


def _artifact(*, critical_findings=()) -> dict:
    return {
        "units": ARTIFACT_UNITS,
        "modules": ARTIFACT_MODULES,
        "entry_points": ("mod_a.py::main",),
        "declared_dependencies": ("dep_a", "dep_b", "dep_c"),
        "declared_api": (
            "process_settlement",
            "normalize_order",
            "missing_api",
        ),
        "observability": {
            "structured_logging": True,
            "metrics": True,
            "distributed_tracing": True,
            "health_checks": True,
            "readiness_checks": True,
            "audit_events": True,
        },
        "critical_findings": tuple(critical_findings),
        "evidence_refs": ("evidence-ec-artifact-hash-0",),
        "provenance": {
            "artifact_hash": "ec-artifact-hash",
            "backend_id": "ec-backend",
        },
    }


def _isr() -> ISR:
    """A harness ISR whose carriers carry verification refs (the trace
    anchors 32.2/32.4 produce), a boundary with no prohibitions, and the
    declared facts 32.6 derives failure obligations from."""
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
        member_refs=("MOD-A",),
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
        verification_refs=("ANCHOR-001",),
    )
    threat = SecurityThreat(
        threat_id="THR-001",
        scenario="an attacker may forge authorization claims",
        severity=ThreatSeverity.HIGH,
        requirement_refs=("REQ-001",),
        invariant_statement="authorization must never be forged",
        architectural_control_refs=(),
        implementation_obligation_refs=(),
        verification_refs=("SEC-TEST-021",),
    )
    reliability = ReliabilityRequirement(
        requirement_id="REL-001",
        target_refs=("MOD-A",),
        failure_modes=(FailureMode.CASCADE_FAILURE,),
        dependency_constraints=("external settlement service",),
    )
    deployment = Deployment(
        id="DEP-001",
        name="Production",
        networking=NetworkingConfig(expose_publicly=True),
        storage=StorageConfig(persistent_storage_required=True),
    )
    intent = DeploymentIntent(
        deployment_id="DEP-INT-001",
        target_refs=("MOD-A",),
        rollout_strategy=RolloutStrategy.CANARY,
        rollout_constraints=("zero-downtime",),
        health_requirements=("healthy for one full cycle",),
        rollback_required=True,
        rollback_target_ref="MOD-A",
    )
    return ISR(
        system=System(
            id="ec-sys",
            name="EvidenceCoverageSystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,),
            architectural_boundaries=(boundary,),
            architectural_decisions=(decision,),
            security_threats=(threat,),
            reliability_requirements=(reliability,),
            deployment=deployment,
            deployment_intents=(intent,),
        )
    )


class EvidenceCoverageHarness:
    """The 32.9 machinery: the seven metric analyzers, the operational
    analyzer, the registry, the availability probe, and the senior-
    quality gate."""

    def __init__(self) -> None:
        self._recipe = CampaignReadinessHarness()
        self._registry = AnalyzerRegistry()
        self._exemplar = ExemplarToolAdapter(
            AnalyzerIdentity(
                analyzer_id="exemplar",
                analyzer_version="1.0.0",
                supported_languages=("python",),
                supported_evidence_classes=("exemplar_inspection",),
            ),
            {"completed": {"findings": ()}},
        )
        self._registry.register(self._exemplar)

    def registry(self) -> AnalyzerRegistry:
        return self._registry

    def artifact(self) -> dict:
        return _artifact()

    def artifact_with_critical(self) -> dict:
        return _artifact(critical_findings=("critical-finding-1",))

    def isr(self) -> ISR:
        return _isr()

    def metric_analyzers(self) -> tuple:
        return (
            CyclomaticComplexityAnalyzer(),
            CodeDuplicationAnalyzer(),
            DeadCodeAnalyzer(),
            UnusedDependenciesAnalyzer(),
            NamingConsistencyAnalyzer(),
            DocumentationCoverageAnalyzer(),
            PublicAPIConsistencyAnalyzer(),
        )

    def operational_analyzer(self) -> OperationalEvidenceAnalyzer:
        return OperationalEvidenceAnalyzer()

    def tool_availability_probe(self) -> ToolAvailabilityProbe:
        return ToolAvailabilityProbe()

    def availability(self):
        return self.tool_availability_probe().probe(self.registry())

    def certify_with_absent_tools(self):
        return type(
            "DimensionCertification",
            (),
            {
                "implementation_quality_state": (
                    implementation_quality_dimension_state(self.availability())
                )
            },
        )()

    def senior_quality_gate(self) -> SeniorQualityCertificationGate:
        return SeniorQualityCertificationGate()

    def matrix_summary(self):
        return self._recipe.matrix_summary()

    def recipe_isr_hash(self):
        return self._recipe.recipe_isr_hash()


@pytest.fixture(scope="module")
def evidence_harness() -> EvidenceCoverageHarness:
    return EvidenceCoverageHarness()


def test_metric_analyzers_deterministic(evidence_harness):
    for analyzer in evidence_harness.metric_analyzers():
        m1 = analyzer.measure(evidence_harness.artifact())
        m2 = analyzer.measure(evidence_harness.artifact())
        assert (m1.metric_id, m1.value) == (m2.metric_id, m2.value)


def test_metric_analyzers_are_emergent_not_authors(evidence_harness):
    """Metrics carry no obligation_id — they measure what IS, never what
    ought to be."""
    assert "obligation_id" not in {
        f.name for f in dataclasses.fields(MetricMeasurement)
    }


def test_all_seven_spec_metrics_implemented(evidence_harness):
    metric_ids = {a.metric_id for a in evidence_harness.metric_analyzers()}
    assert {
        "cyclomatic_complexity",
        "code_duplication",
        "dead_code",
        "unused_dependencies",
        "naming_consistency",
        "documentation_coverage",
        "public_api_consistency",
    } <= metric_ids


def test_tool_absence_is_reported_not_assumed(evidence_harness):
    report = evidence_harness.tool_availability_probe().probe(
        evidence_harness.registry()
    )
    for tool in REQUIRED_EXTERNAL_TOOLS:
        assert tool in report.states
    assert set(report.available) | set(report.not_installed) == set(
        REQUIRED_EXTERNAL_TOOLS
    )


def test_unproven_dimension_marked_unproven_not_proven(evidence_harness):
    """Implementation Quality is PROVEN only for executed tools; absent
    tools → UNPROVEN."""
    result = evidence_harness.certify_with_absent_tools()
    assert result.implementation_quality_state in (
        "PARTIALLY_PROVEN",
        "UNPROVEN",
    )
    assert result.implementation_quality_state != "PROVEN"


def test_senior_contract_has_no_composite_score(evidence_harness):
    verdict = evidence_harness.senior_quality_gate().evaluate(
        evidence_harness.artifact(),
        evidence_harness.isr(),
        evidence_harness.availability(),
    )
    assert not hasattr(verdict, "aggregate_score")
    assert not hasattr(verdict, "quality_score")
    assert len(verdict.criteria) == 10
    assert verdict.verdict is EngineeringVerdict.QUALIFIED_PARTIAL


def test_every_criterion_has_calibration_provenance(evidence_harness):
    for criterion in SENIOR_QUALITY_CONTRACT.criteria:
        assert criterion.calibration_basis
        assert criterion.gate
        assert criterion.evidence_binding


def test_critical_failure_blocks_certified(evidence_harness):
    verdict = evidence_harness.senior_quality_gate().evaluate(
        evidence_harness.artifact_with_critical(),
        evidence_harness.isr(),
        evidence_harness.availability(),
    )
    assert verdict.verdict is not EngineeringVerdict.CERTIFIED
    assert verdict.verdict is EngineeringVerdict.NOT_CERTIFIED


def test_operational_surface_evidenced(evidence_harness):
    measurements = evidence_harness.operational_analyzer().measure(
        evidence_harness.artifact()
    )
    assert {m.metric_id for m in measurements} >= {
        "structured_logging",
        "metrics",
        "health_checks",
    }


def test_matrix_and_recipe_identity_unchanged(evidence_harness):
    assert evidence_harness.matrix_summary() == (12, 18, 0, 0)
    assert evidence_harness.recipe_isr_hash() == RECIPE_HASH