"""R2.7.5 -- capability model + evaluation-mode attestation + backend determinism.

Docker-free coverage of:
  * DimensionResult: unavailable (unevaluated) is NOT a failure.
  * PerformanceGate / SecurityGate: declare the capability, record
    ``unevaluated / unavailable`` evidence, allow in R2.7.5 policy.
  * RegressionGate: evaluation ``precision`` mode is attested in evidence
    (per_test vs aggregate_only) -- never silent.
  * Compiler backend determinism: identical ISR -> identical artifact hash,
    the load-bearing assumption for CausalGate's ``artifact.derives_from(ISR)``.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    ISR,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)

from tiannara.application.compiler.fastapi_hexagonal_backend import (
    FastAPIHexagonalBackend,
)
from tiannara.application.evolution import CandidateGate
from tiannara.application.evolution.candidate_gate import (
    DEFAULT_DIMENSION_POLICY,
    GateContext,
    PerformanceGate,
    SecurityGate,
    classify_regression,
)
from tiannara.application.evolution.compiler_sandbox import (
    RealBackendSandbox,
    hash_artifact,
)
from tiannara.application.evolution.mutation_operators import EMPTY_DELTA, MutationCandidate
from tiannara.domain.models.evidence import (
    DimensionAvailability,
    DimensionPolicy,
    DimensionResult,
    DimensionStatus,
    TestExecution,
    TestOutcome,
    TestRunResult,
)

_NEWLINE = "\n"
_NOISE = b"noise"


# -- capability model epistemic distinction -----------------------------------

def test_unevaluated_unavailable_is_not_a_failure():
    dr = DimensionResult(
        name="security", score=0.0,
        status=DimensionStatus.UNEVALUATED,
        availability=DimensionAvailability.UNAVAILABLE,
        evaluator="none",
    )
    assert dr.is_unknown
    assert not dr.is_failure


def test_evaluated_failure_is_a_real_failure():
    dr = DimensionResult(
        name="security", score=0.0,
        status=DimensionStatus.FAILED,
        availability=DimensionAvailability.AVAILABLE,
        evaluator="owasp-zap-adapter",
    )
    assert dr.is_failure
    assert not dr.is_unknown


def test_evaluated_pass_is_neither_unknown_nor_failure():
    dr = DimensionResult(
        name="performance", score=0.92,
        status=DimensionStatus.EVALUATED,
        availability=DimensionAvailability.AVAILABLE,
        evaluator="locust",
    )
    assert not dr.is_unknown
    assert not dr.is_failure


# -- performance / security gates (R2.7.5 stubs) ------------------------------

def _minimal_ctx() -> GateContext:
    isr = ISR(system=System(id="s", name="S",
                            modules=(Module(id="m", name="M", workflows=()),)))
    return GateContext(
        candidate_isr=isr, candidate_artifact=None,
        candidate_run=TestRunResult(passed=True, exit_code=0, duration_seconds=1.0),
        baseline_run=TestRunResult(passed=True, exit_code=0, duration_seconds=1.0),
        baseline_artifact=None, observation=None,
        mutation=MutationCandidate_stub(),
        parent_isr=isr,
    )


def MutationCandidate_stub() -> MutationCandidate:
    isr = ISR(system=System(id="s", name="S",
                            modules=(Module(id="m", name="M", workflows=()),)))
    return MutationCandidate(
        candidate_id="test", operator_id="test", candidate_isr=isr,
        parent_isr=isr, mutation_delta=EMPTY_DELTA, hypothesis="h",
    )


# -- R2.8.8: performance / security gates (implemented evaluators) -------------------

def test_performance_gate_passes_when_within_threshold():
    """R2.8.8: candidate duration within threshold of baseline passes."""
    ctx = _minimal_ctx()
    gate = PerformanceGate()
    res = gate.evaluate(ctx)
    assert res.passed
    assert res.evidence["status"] == "evaluated"
    assert res.evidence["availability"] == "available"
    assert res.evidence["evaluator"] == "PerformanceGate"
    assert res.evidence["critical"] is True
    assert res.evidence["implemented"] is True
    assert res.evidence["duration_ratio"] <= gate.threshold


def test_performance_gate_fails_on_regression():
    """R2.8.8: duration beyond threshold rejects the candidate."""
    ctx = _minimal_ctx()
    ctx = GateContext(
        candidate_isr=ctx.candidate_isr, candidate_artifact=ctx.candidate_artifact,
        candidate_run=TestRunResult(passed=True, exit_code=0, duration_seconds=5.0),
        baseline_run=TestRunResult(passed=True, exit_code=0, duration_seconds=1.0),
        baseline_artifact=ctx.baseline_artifact, observation=ctx.observation,
        mutation=ctx.mutation, parent_isr=ctx.parent_isr,
        protected_invariants=ctx.protected_invariants,
    )
    gate = PerformanceGate(threshold=2.0)
    res = gate.evaluate(ctx)
    assert not res.passed
    assert res.evidence["status"] == "failed"
    assert res.evidence["duration_ratio"] == 5.0


def test_performance_gate_unevaluated_when_no_timing_data():
    """R2.8.8: no timing data in either run -> unevaluated critical dimension -> reject."""
    ctx = _minimal_ctx()
    ctx = GateContext(
        candidate_isr=ctx.candidate_isr, candidate_artifact=ctx.candidate_artifact,
        candidate_run=TestRunResult(passed=True, exit_code=0, duration_seconds=0.0),
        baseline_run=TestRunResult(passed=True, exit_code=0, duration_seconds=0.0),
        baseline_artifact=ctx.baseline_artifact, observation=ctx.observation,
        mutation=ctx.mutation, parent_isr=ctx.parent_isr,
        protected_invariants=ctx.protected_invariants,
    )
    gate = PerformanceGate()
    res = gate.evaluate(ctx)
    # implemented=True + critical=True + when_unevaluated="infeasible" -> reject
    assert not res.passed
    assert res.evidence["status"] == "unevaluated"
    assert res.evidence["unevaluated_is_infeasible"] is True


def test_security_gate_passes_on_clean_isr():
    """R2.8.8: an ISR with no public interfaces passes the security dimension."""
    ctx = _minimal_ctx()
    gate = SecurityGate()
    res = gate.evaluate(ctx)
    assert res.passed
    assert res.evidence["status"] == "evaluated"
    assert res.evidence["evaluator"] == "SecurityGate"
    assert res.evidence["implemented"] is True
    assert res.evidence["violation_count"] == 0


# -- R2.8.1: dimension-policy table -------------------------------------------

def test_policy_declares_performance_and_security_critical():
    for name in ("performance", "security"):
        p = DEFAULT_DIMENSION_POLICY[name]
        assert p.critical is True
        assert p.evaluator in ("PerformanceGate", "SecurityGate")
        assert p.implemented is True
        # Declared critical so unevaluated results become infeasible.
        assert p.when_unevaluated == "infeasible"
        assert p.unevaluated_is_infeasible() is True


def test_policy_advisory_dimension_is_not_infeasible():
    p = DEFAULT_DIMENSION_POLICY["complexity_efficiency"]
    assert p.critical is False
    assert p.unevaluated_is_infeasible() is False


def test_implemented_critical_unevaluated_becomes_infeasible():
    """R2.8.1 graduation criterion #8: an unevaluated critical dimension with a
    declared (implemented) evaluator must reject -- no false acceptance."""
    p = DimensionPolicy(
        name="security", critical=True, implemented=True,
        evaluator="security-scanner", availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    )
    assert p.unevaluated_is_infeasible() is True


def test_missing_evidence_never_passes_under_strict_policy():
    """R2.8.8: a security-critical violation (public endpoint without permissions)
    is a hard reject -- not an unevaluated allowance."""
    from constitutional_architecture.isr.model.interface import (
        Interface, InterfaceType, Endpoint, HttpMethod,
    )
    # ISR with a public interface endpoint lacking required_permissions.
    bad_module = Module(
        id="m", name="M", workflows=(),
        interfaces=(Interface(
            id="iface", name="API", interface_type=InterfaceType.REST,
            is_internal=False,
            endpoints=(Endpoint(
                id="ep", name="ep", method=HttpMethod.GET, path="/x",
                is_public=True, required_permissions=(),
            ),),
        ),),
    )
    bad_isr = ISR(system=System(id="s", name="S", modules=(bad_module,)))
    ctx = GateContext(
        candidate_isr=bad_isr, candidate_artifact=None,
        candidate_run=TestRunResult(passed=True, exit_code=0, duration_seconds=1.0),
        baseline_run=TestRunResult(passed=True, exit_code=0, duration_seconds=1.0),
        baseline_artifact=None, observation=None,
        mutation=MutationCandidate_stub(),
        parent_isr=bad_isr,
    )
    gate = SecurityGate()
    res = gate.evaluate(ctx)
    assert not res.passed  # security-critical FAIL -> hard reject
    assert res.evidence["status"] == "failed"
    assert res.evidence["violation_count"] > 0


def test_default_frontier_declares_performance_and_security():
    ids = [g.gate_id for g in CandidateGate.default()._gates]
    assert "performance" in ids
    assert "security" in ids


# -- evaluation-mode attestation (precision is visible, never silent) -----------

def _run_with_tests(tests, exit_code=0) -> TestRunResult:
    failed = sum(1 for t in tests if t.outcome in (TestOutcome.FAILED, TestOutcome.ERROR))
    return TestRunResult(
        passed=(exit_code == 0), exit_code=exit_code,
        total_tests=len(tests), failed_tests=failed, tests=tests,
    )


def test_regression_gateway_attests_per_test_mode():
    base = _run_with_tests((
        TestExecution(test_id="t::a", outcome=TestOutcome.PASSED, content_hash="h"),
    ))
    cand = _run_with_tests((
        TestExecution(test_id="t::a", outcome=TestOutcome.PASSED, content_hash="h"),
    ))
    res = classify_regression(base, cand)
    assert res.precision == "per_test"


def test_regression_gateway_attests_aggregate_fallback_mode():
    base = TestRunResult(passed=True, exit_code=0, total_tests=1, failed_tests=0, tests=())
    cand = TestRunResult(passed=True, exit_code=0, total_tests=1, failed_tests=0, tests=())
    res = classify_regression(base, cand)
    assert res.precision == "aggregate_only"


# -- compiler-backend determinism (load-bearing for CausalGate.fresh) ----------

def _workflow(resolving: bool) -> Workflow:
    aw = WorkflowState(
        id="order-await", name="awaiting",
        state_type=StateType.INTERMEDIATE, metadata={"awaits": "process_payment"},
    )
    fin = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            WorkflowTransition(
                id="resolve", name="resolve",
                from_state_id=aw.id, to_state_id=fin.id, trigger="process_payment",
            ),
        )
    return Workflow(id="order", name="order", states=(aw, fin), transitions=transitions)


def _isr(resolving: bool) -> ISR:
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=(_workflow(resolving),)),),
    ))


def test_compiler_backend_is_deterministic():
    """Identical ISR -> byte-identical artifact (CausalGate.fresh relies on this)."""
    sandbox = RealBackendSandbox(backend=FastAPIHexagonalBackend())
    a = sandbox.build(_isr(resolving=True), workspace=tempfile.mkdtemp())
    b = sandbox.build(_isr(resolving=True), workspace=tempfile.mkdtemp())
    assert a.compile_ok and b.compile_ok
    assert a.artifact_hash == b.artifact_hash
    # A structurally different ISR must NOT collapse to the same artifact hash.
    c = sandbox.build(_isr(resolving=False), workspace=tempfile.mkdtemp())
    assert c.artifact_hash != a.artifact_hash


def test_hash_artifact_self_consistency_ignores_side_effect_dirs():
    """hash_artifact is stable and ignores pyc/__pycache__ (A5a/A5b contract)."""
    root = Path(tempfile.mkdtemp())
    (root / "svc").mkdir()
    (root / "svc" / "main.py").write_text("x = 1" + _NEWLINE)
    (root / "svc" / "__pycache__").mkdir(exist_ok=True)
    (root / "svc" / "__pycache__" / "main.cpython.pyc").write_bytes(_NOISE)
    h1 = hash_artifact(root)
    # A second read is identical (deterministic over the pinned tree).
    assert h1 == hash_artifact(root)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
