from app.engine.requirement_analyzer import (
    analyze_requirements, classify_statement, decompose_statements,
)
from app.engine.requirement_ir import Requirement, RequirementKind


def test_decomposition_creates_traceable_requirements():
    result = decompose_statements(["Create a wallet", "Authenticate every caller"])
    assert result.graph.requirements["R-001"].kind is RequirementKind.FUNCTIONAL
    assert result.graph.requirements["R-002"].kind is RequirementKind.SECURITY
    assert result.graph.traceability()["R-001"]["acceptance_criteria"] == ["AC-001"]
    assert result.ready_for_isr


def test_ambiguous_input_blocks_isr_readiness():
    result = decompose_statements(["The API must be fast"])
    assert not result.ready_for_isr
    assert any("unresolved ambiguity" in i.message for i in result.unresolved)


def test_existing_requirements_are_analyzed_without_mutating_them():
    req = Requirement("R-WALLET", "Transfer funds atomically", RequirementKind.FUNCTIONAL)
    result = analyze_requirements([req])
    assert result.graph.requirements["R-WALLET"] == req
    assert not result.ready_for_isr


def test_classification_is_deterministic():
    assert classify_statement("API latency must be within 200ms") is RequirementKind.NON_FUNCTIONAL
    assert classify_statement("Must authenticate every caller") is RequirementKind.SECURITY
    assert classify_statement("Deploy with health checks") is RequirementKind.OPERATIONAL
