from tiannara.application.publisher.gate_evaluator import GatePolicy, ExitGateEvaluator
from tiannara.domain.models.evidence import (
    CertificationEvidence,
    GateStatus,
    TestRunResult,
)


def _ev(compilation_success=True, test_run=None, sec_performed=False, vulns=0):
    return CertificationEvidence(
        project_id="p", isr_hash="h", genome_id="g", backend_name="m",
        compilation_success=compilation_success,
        test_run=test_run,
        security_scan_performed=sec_performed,
        security_vulnerabilities=vulns,
    )


def test_all_gates_pass():
    policy = GatePolicy(
        min_test_pass_rate=0.9, require_compilation=True,
        require_security_scan=True, max_security_vulnerabilities=0,
    )
    ev = _ev(
        test_run=TestRunResult(passed=True, exit_code=0, total_tests=10, failed_tests=0),
        sec_performed=True,
    )
    passed, results = ExitGateEvaluator(policy).evaluate(ev)
    assert passed
    assert all(r.status is GateStatus.PASS for r in results)


def test_compilation_failure_blocks():
    policy = GatePolicy(
        min_test_pass_rate=0.9, require_compilation=True,
        require_security_scan=False, max_security_vulnerabilities=0,
    )
    passed, _ = ExitGateEvaluator(policy).evaluate(_ev(compilation_success=False))
    assert passed is False


def test_test_pass_rate_below_threshold_fails():
    policy = GatePolicy(
        min_test_pass_rate=0.99, require_compilation=True,
        require_security_scan=False, max_security_vulnerabilities=0,
    )
    ev = _ev(test_run=TestRunResult(passed=False, exit_code=1, total_tests=100, failed_tests=10))
    passed, _ = ExitGateEvaluator(policy).evaluate(ev)
    assert passed is False


def test_security_violation_blocks():
    policy = GatePolicy(
        min_test_pass_rate=0.9, require_compilation=True,
        require_security_scan=True, max_security_vulnerabilities=0,
    )
    ev = _ev(sec_performed=True, vulns=3)
    passed, _ = ExitGateEvaluator(policy).evaluate(ev)
    assert passed is False


def test_no_test_run_is_not_evaluated():
    policy = GatePolicy(
        min_test_pass_rate=0.9, require_compilation=True,
        require_security_scan=False, max_security_vulnerabilities=0,
    )
    ev = _ev()
    passed, results = ExitGateEvaluator(policy).evaluate(ev)
    tests = [r for r in results if r.gate == "tests"][0]
    assert tests.status is GateStatus.NOT_EVALUATED
    assert passed is True
