from tiannara.application.certification.hardening_certification import (
    certify_generated_application,
    evaluate_hardening_certification,
)
from tiannara.application.hardening.fullstack_gates import (
    FULLSTACK_HARDENING_GATES,
    GateResult,
    GateStatus,
)


def _passing_results():
    return [
        GateResult(g.gate_id, GateStatus.PASS, (f"evidence:{g.gate_id}",))
        for g in FULLSTACK_HARDENING_GATES
    ]


def test_absent_gates_are_unknown_and_block_certification():
    result = evaluate_hardening_certification(
        [GateResult("BACKEND-BUILD", GateStatus.PASS)]
    )
    assert result.certified is False
    assert any(blocker.startswith("REQ-TRACE:unknown") for blocker in result.blockers)


def test_not_applicable_does_not_bypass_required_gate():
    results = _passing_results()
    results[-1] = GateResult("EVIDENCE", GateStatus.NOT_APPLICABLE)
    result = evaluate_hardening_certification(results)
    assert result.certified is False
    assert "EVIDENCE:not_applicable" in result.blockers


def test_compilation_success_alone_is_not_certification():
    result = certify_generated_application(compilation_ok=True, gate_results=())
    assert result.certified is False
    assert len(result.blockers) == len(FULLSTACK_HARDENING_GATES)


def test_complete_runtime_evidence_can_certify():
    result = certify_generated_application(
        compilation_ok=True,
        gate_results=_passing_results(),
    )
    assert result.certified is True
    assert result.blockers == ()


def test_compilation_failure_blocks_even_with_all_gate_results_passing():
    result = certify_generated_application(
        compilation_ok=False,
        gate_results=_passing_results(),
    )
    assert result.certified is False
    assert result.blockers[0] == "COMPILATION:fail"
