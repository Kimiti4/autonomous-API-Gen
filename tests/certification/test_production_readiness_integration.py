import pytest
from tiannara.application.certification.production_readiness import CertificationEvidence, DimensionVerdict, ProductionReadinessGate, ProductionReadinessVerdict, BlockingDimension, REQUIRED_DIMENSIONS
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent, EventType

def _ev(dim, verdict, criticals=0, refs=("ref-1",)):
    return CertificationEvidence(dim, verdict, criticals, refs, content_hash=f"h-{dim}")

def _ledger_with_refs(refs):
    l=EvolutionLedger()
    for r in refs:
        ev=EvolutionEvent(event_id=r, evolution_id="test", sequence=0, event_type=EventType.CERTIFICATION, subject_id="test", payload={"ref": r})
        l.append_event(ev, evolution_id="test")
    return l

@pytest.fixture
def gate():
    refs=("ref-1",)
    ledger=_ledger_with_refs(refs)
    return ProductionReadinessGate(ledger)

FULL_CERTIFIED = {
    "compiler": _ev("compiler", DimensionVerdict.CERTIFIED),
    "engineering": _ev("engineering", DimensionVerdict.CERTIFIED),
    "security": _ev("security", DimensionVerdict.CERTIFIED),
    "resilience": _ev("resilience", DimensionVerdict.CERTIFIED),
}

def test_artifact_c_all_certified_is_ready(gate):
    result = gate.evaluate(FULL_CERTIFIED)
    assert result.verdict is ProductionReadinessVerdict.PRODUCTION_READY
    assert result.blocking_dimensions == ()

def test_artifact_a_security_failure_masks_nothing(gate):
    evidence = dict(FULL_CERTIFIED)
    evidence["security"] = _ev("security", DimensionVerdict.NOT_CERTIFIED)
    result = gate.evaluate(evidence)
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert BlockingDimension("security", "NOT_CERTIFIED") in result.blocking_dimensions

def test_artifact_b_bounded_resilience_is_not_ready(gate):
    evidence = dict(FULL_CERTIFIED)
    evidence["resilience"] = _ev("resilience", DimensionVerdict.BOUNDED)
    result = gate.evaluate(evidence)
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert BlockingDimension("resilience", "BOUNDED") in result.blocking_dimensions

def test_not_tested_blocks(gate):
    evidence = dict(FULL_CERTIFIED)
    evidence["compiler"] = _ev("compiler", DimensionVerdict.NOT_TESTED)
    assert gate.evaluate(evidence).verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY

def test_critical_violation_blocks_even_when_certified(gate):
    evidence = dict(FULL_CERTIFIED)
    evidence["security"] = _ev("security", DimensionVerdict.CERTIFIED, criticals=1)
    result = gate.evaluate(evidence)
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert BlockingDimension("security", "CRITICAL_VIOLATION") in result.blocking_dimensions

def test_absent_dimension_blocks(gate):
    evidence = {k: v for k, v in FULL_CERTIFIED.items() if k != "resilience"}
    result = gate.evaluate(evidence)
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert BlockingDimension("resilience", "ABSENT") in result.blocking_dimensions

def test_unresolved_evidence_blocks():
    ledger=EvolutionLedger()
    gate2=ProductionReadinessGate(ledger)
    result = gate2.evaluate(FULL_CERTIFIED)
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert any(b.reason == "UNRESOLVED_EVIDENCE" for b in result.blocking_dimensions)

def test_single_failure_blocks_regardless_of_majority(gate):
    for n_fail in range(1, 5):
        evidence = dict(FULL_CERTIFIED)
        for dim in REQUIRED_DIMENSIONS[:n_fail]:
            evidence[dim] = _ev(dim, DimensionVerdict.NOT_CERTIFIED)
        assert gate.evaluate(evidence).verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY

def test_no_composite_or_average_score(gate):
    import ast, inspect
    src = inspect.getsource(ProductionReadinessGate).lower()
    for token in ("average", "weight", "composite", "score", "mean("):
        assert token not in src, f"forbidden aggregation token: {token}"

def test_result_carries_no_score_field(gate):
    result = gate.evaluate(FULL_CERTIFIED)
    assert not hasattr(result, "score") and not hasattr(result, "readiness_score")

def test_gate_cannot_mutate_verdicts(gate):
    import ast, inspect
    tree = ast.parse(inspect.getsource(ProductionReadinessGate))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "set_verdict" not in fn and "override" not in fn and "upgrade" not in fn

def test_first_blocking_dimension_is_named(gate):
    evidence = dict(FULL_CERTIFIED)
    evidence["engineering"] = _ev("engineering", DimensionVerdict.BOUNDED)
    result = gate.evaluate(evidence)
    assert result.blocking_dimensions[0].dimension == "engineering"
    assert result.blocking_dimensions[0].reason == "BOUNDED"

def test_readiness_is_ledger_addressable(gate):
    result = gate.evaluate(FULL_CERTIFIED)
    assert gate.ledger.event_by_ref(result.readiness_event_ref) is not None
    assert gate.ledger.verify_event_chain() is True

def test_matrix_and_recipe_identity_unchanged(gate):
    assert gate.matrix_summary() == (12, 18, 0, 0)
    assert gate.recipe_isr_hash() == "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
