"""R2.8.8 -- Performance + Security Evaluators: real dimensions on the frontier.

The performance and security dimensions are no longer stubs: they are real,
ISR-authoritative, technology-agnostic evaluators with threshold policy
(not hard-coded in the compiler). A security_critical=FAIL is a hard
feasibility constraint: correctness=1, security=0 -> infeasible, never
Pareto-selected.
"""
from __future__ import annotations

import pytest

from constitutional_architecture.isr.model import (
    ISR, Module, System,
    Interface, InterfaceType, Endpoint, HttpMethod,
    Service, Operation, OperationType,
    Policy, PolicyType, PolicyRule,
    Workflow, WorkflowState, WorkflowTransition, StateType,
)

from tiannara.application.evolution import (
    GateContext, PerformanceGate, SecurityGate, CandidateGate,
)
from tiannara.application.evolution.candidate_gate import (
    DEFAULT_DIMENSION_POLICY,
)
from tiannara.application.evolution.mutation_operators import EMPTY_DELTA, MutationCandidate
from tiannara.domain.models.evidence import (
    DimensionAvailability, DimensionStatus,
    TestRunResult,
)


def _stub_mutation(isr: ISR) -> MutationCandidate:
    return MutationCandidate(
        candidate_id="test", operator_id="test", candidate_isr=isr,
        parent_isr=isr, mutation_delta=EMPTY_DELTA, hypothesis="h",
    )


def _ctx(isr: ISR, *,
         cand_duration: float = 1.0, base_duration: float = 1.0,
         cand_passed: bool = True, base_passed: bool = True) -> GateContext:
    return GateContext(
        candidate_isr=isr, candidate_artifact=None,
        candidate_run=TestRunResult(
            passed=cand_passed, exit_code=0 if cand_passed else 1,
            duration_seconds=cand_duration),
        baseline_run=TestRunResult(
            passed=base_passed, exit_code=0 if base_passed else 1,
            duration_seconds=base_duration),
        baseline_artifact=None, observation=None,
        mutation=_stub_mutation(isr),
        parent_isr=isr,
    )


def _clean_isr() -> ISR:
    """ISR with no public interfaces -- security-safe by construction."""
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=()),)))


# --- performance: regression is a hard constraint ------------------------------

def test_performance_within_threshold_passes():
    gate = PerformanceGate(threshold=2.0)
    ctx = _ctx(_clean_isr(), cand_duration=1.5, base_duration=1.0)
    res = gate.evaluate(ctx)
    assert res.passed
    assert res.evidence["status"] == "evaluated"


def test_performance_regression_rejects():
    gate = PerformanceGate(threshold=2.0)
    ctx = _ctx(_clean_isr(), cand_duration=3.0, base_duration=1.0)
    res = gate.evaluate(ctx)
    assert not res.passed
    assert res.evidence["status"] == "failed"


def test_performance_improvement_always_passes():
    """A faster candidate is never penalized."""
    gate = PerformanceGate(threshold=2.0)
    ctx = _ctx(_clean_isr(), cand_duration=0.1, base_duration=1.0)
    res = gate.evaluate(ctx)
    assert res.passed


def test_performance_no_timing_data_is_infeasible():
    """When timing data is absent, the critical implemented dimension rejects."""
    gate = PerformanceGate()
    ctx = _ctx(_clean_isr(), cand_duration=0.0, base_duration=0.0)
    res = gate.evaluate(ctx)
    assert not res.passed
    assert res.evidence["status"] == "unevaluated"


def test_performance_threshold_is_configurable():
    """Thresholds come from policy/constructor, not hard-coded in compiler."""
    gate_default = PerformanceGate()
    gate_strict = PerformanceGate(threshold=1.1)
    isr = _clean_isr()
    ctx = _ctx(isr, cand_duration=1.5, base_duration=1.0)
    assert gate_default.evaluate(ctx).passed       # 1.5x <= 2.0x -> pass
    assert not gate_strict.evaluate(ctx).passed     # 1.5x > 1.1x -> reject


# --- security: ISR-authoritative checks -----------------------------------------

def _isr_with_public_endpoint_no_perms() -> ISR:
    """ISR with a public REST endpoint lacking required_permissions."""
    ep = Endpoint(
        id="ep", name="ep", method=HttpMethod.GET, path="/x",
        is_public=True, required_permissions=(),
    )
    iface = Interface(
        id="iface", name="API", interface_type=InterfaceType.REST,
        is_internal=False,
        endpoints=(ep,),
    )
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=(),
                              interfaces=(iface,),),)))


def _isr_with_public_operation_no_perms() -> ISR:
    """ISR with a public service operation lacking required_permissions."""
    op = Operation(
        id="op", name="op", operation_type=OperationType.COMMAND,
        is_public=True, required_permissions=(),
    )
    svc = Service(id="svc", name="SVC", operations=(op,))
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=(),
                              services=(svc,),),)))


def _isr_with_secured_public_endpoint() -> ISR:
    """ISR where the public endpoint has required_permissions (clean)."""
    ep = Endpoint(
        id="ep", name="ep", method=HttpMethod.GET, path="/x",
        is_public=True, required_permissions=("auth:read",),
    )
    iface = Interface(
        id="iface", name="API", interface_type=InterfaceType.REST,
        is_internal=False, secured_by_policy_id="authz",
        endpoints=(ep,),
    )
    pol = Policy(id="authz", name="AuthZ", policy_type=PolicyType.AUTHORIZATION)
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=(),
                              interfaces=(iface,), policies=(pol,),),)))


def test_security_rejects_public_endpoint_without_perms():
    gate = SecurityGate()
    ctx = _ctx(_isr_with_public_endpoint_no_perms())
    res = gate.evaluate(ctx)
    assert not res.passed
    assert res.evidence["status"] == "failed"
    assert res.evidence["public_endpoint_no_perms"] == 1


def test_security_rejects_public_operation_without_perms():
    gate = SecurityGate()
    ctx = _ctx(_isr_with_public_operation_no_perms())
    res = gate.evaluate(ctx)
    assert not res.passed
    assert res.evidence["status"] == "failed"
    assert res.evidence["public_op_no_perms"] == 1


def test_security_accepts_secured_public_endpoint():
    gate = SecurityGate()
    ctx = _ctx(_isr_with_secured_public_endpoint())
    res = gate.evaluate(ctx)
    assert res.passed
    assert res.evidence["status"] == "evaluated"
    assert res.evidence["violation_count"] == 0


def test_security_accepts_clean_internal_isr():
    gate = SecurityGate()
    ctx = _ctx(_clean_isr())
    res = gate.evaluate(ctx)
    assert res.passed
    assert res.evidence["status"] == "evaluated"


# --- dimension policy: implemented + critical ----------------------------------

def test_performance_and_security_policies_are_implemented_and_available():
    for name in ("performance", "security"):
        p = DEFAULT_DIMENSION_POLICY[name]
        assert p.implemented is True
        assert p.critical is True
        assert p.availability == DimensionAvailability.AVAILABLE
        assert p.evaluator in ("PerformanceGate", "SecurityGate")


# --- gate frontier integrates both gates ---------------------------------------

def test_default_frontier_runs_performance_and_security():
    gate = CandidateGate.default()
    ids = [g.gate_id for g in gate._gates]
    assert "performance" in ids
    assert "security" in ids


def test_candidate_verdict_aggregates_security_reject():
    """A security violation must reject at the security+perf frontier."""
    from tiannara.application.evolution.candidate_gate import CandidateGate
    gate = CandidateGate((PerformanceGate(threshold=2.0), SecurityGate()))
    bad_isr = _isr_with_public_endpoint_no_perms()
    ctx = _ctx(bad_isr)
    verdict = gate.evaluate(ctx)
    assert not verdict.accept
    sec_result = next(r for r in verdict.gate_results if r.gate_id == "security")
    assert not sec_result.passed


def test_candidate_verdict_accept_when_all_gates_pass():
    """A clean ISR with good performance is accepted by the security+perf frontier."""
    from tiannara.application.evolution.candidate_gate import CandidateGate
    gate = CandidateGate((PerformanceGate(threshold=2.0), SecurityGate()))
    ctx = _ctx(_clean_isr(), cand_duration=0.5, base_duration=1.0)
    verdict = gate.evaluate(ctx)
    perf = next(r for r in verdict.gate_results if r.gate_id == "performance")
    sec = next(r for r in verdict.gate_results if r.gate_id == "security")
    assert perf.passed
    assert sec.passed
    assert verdict.accept


def test_candidate_verdict_rejects_on_security_failure():
    """A security violation rejects the candidate at the security+perf frontier."""
    from tiannara.application.evolution.candidate_gate import CandidateGate
    gate = CandidateGate((PerformanceGate(threshold=2.0), SecurityGate()))
    ctx = _ctx(_isr_with_public_endpoint_no_perms())
    verdict = gate.evaluate(ctx)
    assert not verdict.accept
    sec = next(r for r in verdict.gate_results if r.gate_id == "security")
    assert not sec.passed


def test_candidate_verdict_rejects_on_performance_failure():
    """A performance regression rejects the candidate at the security+perf frontier."""
    from tiannara.application.evolution.candidate_gate import CandidateGate
    gate = CandidateGate((PerformanceGate(threshold=2.0), SecurityGate()))
    ctx = _ctx(_clean_isr(), cand_duration=5.0, base_duration=1.0)
    verdict = gate.evaluate(ctx)
    assert not verdict.accept
    perf = next(r for r in verdict.gate_results if r.gate_id == "performance")
    assert not perf.passed
