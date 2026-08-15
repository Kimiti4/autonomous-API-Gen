from dataclasses import dataclass
from ...domain.models.evidence import CertificationEvidence, GateResult, GateStatus


@dataclass(frozen=True)
class GatePolicy:
    """Declarative success criteria. Injected, never hardcoded."""

    min_test_pass_rate: float
    require_compilation: bool
    require_security_scan: bool
    max_security_vulnerabilities: int


class ExitGateEvaluator:
    def __init__(self, policy: GatePolicy) -> None:
        self._policy = policy

    def evaluate(self, evidence: CertificationEvidence) -> tuple[bool, list[GateResult]]:
        results: list[GateResult] = []

        if self._policy.require_compilation:
            ok = evidence.compilation_success
            results.append(GateResult(
                gate="compilation",
                status=GateStatus.PASS if ok else GateStatus.FAIL,
                detail="Compiled successfully" if ok else "Compilation failed",
            ))

        if evidence.test_run is None:
            results.append(GateResult(
                gate="tests", status=GateStatus.NOT_EVALUATED, detail="No test run recorded"))
        else:
            ok = evidence.test_run.pass_rate >= self._policy.min_test_pass_rate
            results.append(GateResult(
                gate="tests",
                status=GateStatus.PASS if ok else GateStatus.FAIL,
                detail=f"pass_rate={evidence.test_run.pass_rate:.3f} required>={self._policy.min_test_pass_rate}",
            ))

        if not evidence.security_scan_performed:
            status = GateStatus.FAIL if self._policy.require_security_scan else GateStatus.NOT_EVALUATED
            results.append(GateResult(gate="security", status=status, detail="No scan performed"))
        else:
            ok = evidence.security_vulnerabilities <= self._policy.max_security_vulnerabilities
            results.append(GateResult(
                gate="security",
                status=GateStatus.PASS if ok else GateStatus.FAIL,
                detail=f"vulnerabilities={evidence.security_vulnerabilities}"))

        passed = all(r.status != GateStatus.FAIL for r in results) and any(
            r.status == GateStatus.PASS for r in results)
        return passed, results
