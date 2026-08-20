"""R2.10.32.7 — The Analyzer Contract: the evidence-production boundary.

The acceptance surface:

    * the three-way distinction is structural: a finding is an
      observation with no verdict/certification surface, and the
      obligation link is OPTIONAL (obligation-linked evidence and
      emergent-property evidence flow through one contract without
      conflation);
    * an obligation link, when present, resolves to an obligation the
      ISR (or a declared derivation from it) already carries — an
      unresolvable link is a contract violation, not a silent drop;
    * every result carries full provenance (who, which version, against
      which artifact, under which configuration, what was observed,
      where the evidence is);
    * the Analyzer protocol has no verdict/obligation-construction
      surface;
    * the reference analyzer is deterministic (replay reproduces the
      execution instance);
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import dataclasses
import inspect

import pytest

from constitutional_architecture.isr.model import (
    ArchitecturalDecision,
    BusinessCapability,
    Entity,
    Module,
    Requirement,
    SecurityThreat,
    ThreatSeverity,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from tiannara.application.quality.analyzer_contract import (
    Analyzer,
    AnalyzerContractViolation,
    AnalyzerFinding,
    AnalyzerResult,
    ReferenceAnalyzer,
    obligation_exists,
    validate_obligation_links,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _isr() -> ISR:
    """A harness ISR carrying the obligation-bearing carriers the contract's
    obligation link may point at: an F requirement, a 32.1 decision, and
    a 32.3 threat."""
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
        verification_refs=(),
    )
    threat = SecurityThreat(
        threat_id="THR-001",
        scenario="an attacker may forge authorization claims",
        severity=ThreatSeverity.HIGH,
        requirement_refs=("REQ-001",),
        invariant_statement="authorization must never be forged",
        architectural_control_refs=(),
        implementation_obligation_refs=(),
        verification_refs=(),
    )
    return ISR(
        system=System(
            id="ac-sys",
            name="AnalyzerContractSystem",
            modules=(module,),
            business_capabilities=(capability,),
            requirements=(requirement,),
            architectural_decisions=(decision,),
            security_threats=(threat,),
        )
    )


def _artifact() -> dict:
    return {
        "modules": (
            {
                "module_id": "MOD-A",
                "entities": ("e1",),
            },
            {
                "module_id": "MOD-B",
                "entities": (),
            },
        ),
        "provenance": {
            "artifact_hash": "ac-artifact-hash",
            "backend_id": "ac-backend",
        },
    }


def _configuration() -> dict:
    return {"configuration_id": "rc-config-v1"}


class AnalyzerContractHarness:
    """The 32.7 machinery: the reference analyzer, the harness artifact and
    configuration, and the obligation-resolution predicate."""

    def __init__(self) -> None:
        self._recipe = CampaignReadinessHarness()
        self._analyzer = ReferenceAnalyzer()
        self._artifact = _artifact()
        self._configuration = _configuration()

    def run_reference_analyzer(self) -> AnalyzerResult:
        return self._analyzer.analyze(self._artifact, self._configuration)

    def obligation_linked_finding(self) -> AnalyzerFinding:
        result = self.run_reference_analyzer()
        linked = []
        for finding in result.findings:
            if finding.finding_id == "MOD-A::reference-inspection":
                linked.append(
                    dataclasses.replace(finding, obligation_id="REQ-001")
                )
            else:
                linked.append(finding)
        return linked[0]

    def emergent_finding(self) -> AnalyzerFinding:
        result = self.run_reference_analyzer()
        return next(
            f
            for f in result.findings
            if f.finding_id == "MOD-B::reference-inspection"
        )

    def isr_obligation_exists(self, obligation_id: str) -> bool:
        return obligation_exists(obligation_id, _isr())

    def matrix_summary(self):
        return self._recipe.matrix_summary()

    def recipe_isr_hash(self):
        return self._recipe.recipe_isr_hash()


@pytest.fixture(scope="module")
def contract_harness() -> AnalyzerContractHarness:
    return AnalyzerContractHarness()


def test_finding_is_observation_not_obligation_or_verdict():
    """Structural: a finding carries no verdict surface, and the obligation
    link is optional — an emergent finding carries none."""
    fields = {f.name for f in dataclasses.fields(AnalyzerFinding)}
    assert "verdict" not in fields
    assert "certification" not in fields
    assert "obligation_id" in fields
    emergent = AnalyzerFinding(
        finding_id="f1",
        analyzer_id="a",
        analyzer_version="1",
        artifact_identity="art",
        configuration_identity="cfg",
        execution_identity="ex",
        severity="ADVISORY",
        category="concentration",
        description="d",
        location=None,
        evidence_refs=(),
        obligation_id=None,
    )
    assert emergent.obligation_id is None


def test_obligation_link_points_at_isr_not_invention(contract_harness):
    """A finding's obligation_id, when present, resolves to an obligation
    the ISR already carries; an unresolvable link is a contract
    violation, not a silent drop."""
    finding = contract_harness.obligation_linked_finding()
    assert finding.obligation_id is not None
    assert contract_harness.isr_obligation_exists(finding.obligation_id)
    result = contract_harness.run_reference_analyzer()
    assert validate_obligation_links(result, _isr()) is None
    invalid = dataclasses.replace(result, findings=(
        dataclasses.replace(
            result.findings[0],
            obligation_id="OBLIGATION-THAT-DOES-NOT-EXIST",
        ),
    ))
    with pytest.raises(AnalyzerContractViolation):
        validate_obligation_links(invalid, _isr())


def test_every_result_carries_full_provenance(contract_harness):
    result = contract_harness.run_reference_analyzer()
    for field in (
        "analyzer_id",
        "analyzer_version",
        "artifact_identity",
        "configuration_identity",
        "execution_identity",
    ):
        assert getattr(result, field)
    assert result.deterministic
    for finding in result.findings:
        assert finding.finding_id
        assert finding.evidence_refs


def test_analyzer_cannot_decide_architectural_truth():
    """Structural: the Analyzer protocol has no verdict/obligation-
    construction surface."""
    members = dict(inspect.getmembers(Analyzer))
    assert "decide_obligation" not in members
    assert "render_verdict" not in members
    assert "analyze" in members
    assert "identity" in members


def test_reference_analyzer_is_deterministic(contract_harness):
    r1 = contract_harness.run_reference_analyzer()
    r2 = contract_harness.run_reference_analyzer()
    assert (r1.findings, r1.artifact_identity) == (
        r2.findings,
        r2.artifact_identity,
    )
    assert r1.execution_identity == r2.execution_identity


def test_two_evidence_modes_coexist_without_conflation(contract_harness):
    """Obligation-linked and obligation-independent evidence both flow
    through the contract, distinguishable, neither forced into the
    other's shape."""
    linked = contract_harness.obligation_linked_finding()
    emergent = contract_harness.emergent_finding()
    assert linked.obligation_id is not None
    assert emergent.obligation_id is None
    assert linked.category == emergent.category


def test_matrix_and_recipe_identity_unchanged(contract_harness):
    assert contract_harness.matrix_summary() == (12, 18, 0, 0)
    assert contract_harness.recipe_isr_hash() == RECIPE_HASH