from tiannara.application.hardening.fullstack_gates import GateResult, GateStatus, certify_hardening

def test_missing_gate_cannot_certify():
    assert not certify_hardening(())

def test_unknown_gate_cannot_certify():
    assert not certify_hardening([GateResult("REQ-TRACE",GateStatus.UNKNOWN)])

def test_all_required_gates_must_pass():
    from tiannara.application.hardening.fullstack_gates import FULLSTACK_HARDENING_GATES
    results=[GateResult(g.gate_id,GateStatus.PASS,("evidence",)) for g in FULLSTACK_HARDENING_GATES]
    assert certify_hardening(results)
    results[-1]=GateResult(results[-1].gate_id,GateStatus.FAIL)
    assert not certify_hardening(results)
