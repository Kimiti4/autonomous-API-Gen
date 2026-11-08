"""CP067-R5 supplement — W03 closure assessment and W10 integration verification (narrow)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from certification.isr_independent_verification.w03_revision_integrity_verification import (
    INDEPENDENT_VERIFIER_W03,
    run_w03_revision_integrity_verification,
)
from certification.isr_independent_verification.wave10_integration_gate import (
    GateResult,
    run_wave10_integration_gate,
)
from certification.orchestration.ingress_revision_integrity_gate import W08_W03_BOUNDARY_IDS
from certification.orchestration.ingress_trust_matrix import (
    EnforcementStatus,
    ingress_trust_matrix,
)

INDEPENDENT_VERIFIER_R5_CLOSURE = (
    "certification.isr_independent_verification.r5_w03_w10_closure_assessment.v1"
)

EXPECTED_W10_GATE_COUNT = 17
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WAVE_LEDGER = WORKSPACE_ROOT / "certification/atlas/esap/cp067_r2_wave0_authorization.json"


class AssessmentCheck(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ADVISORY = "ADVISORY"


@dataclass(frozen=True)
class AssessmentRow:
    check_id: str
    result: AssessmentCheck
    detail: str


@dataclass(frozen=True)
class R5W03W10ClosureAssessment:
    verifier_id: str
    checks: tuple[AssessmentRow, ...]
    w03_iv_passed: bool
    w10_gate_count: int
    w10_integration_passed: bool
    dashboard_ingress_status: str
    r1_w03_closure_claimed: bool
    r1_w08_closure_claimed: bool
    w08_universal_closure_claimed: bool
    next_incomplete_dependencies: tuple[str, ...]
    assessment_passed: bool
    findings: tuple[str, ...]


def _check_w03_iv() -> AssessmentRow:
    report = run_w03_revision_integrity_verification()
    detail = (
        f"slice={report.slice_integrity_passed}; tamper={report.tamper_detection_passed}; "
        f"verifier={INDEPENDENT_VERIFIER_W03}"
    )
    ok = report.passed
    return AssessmentRow(
        "C1-W03-WORKLOAD-AND-TAMPER",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        detail,
    )


def _check_http_preflight_order() -> AssessmentRow:
    path = WORKSPACE_ROOT / "tiannara/application/orchestration/production_ingress.py"
    text = path.read_text(encoding="utf-8")
    anchor = text.find("def execute_governed_full_stack_ingress")
    if anchor < 0:
        return AssessmentRow(
            "C2-HTTP-PREFLIGHT-BEFORE-CANONICAL",
            AssessmentCheck.FAILED,
            "missing-execute_governed_full_stack_ingress",
        )
    body = text[anchor:]
    integrity = body.find("assert_workload_revision_integrity_at_ingress(")
    canonical = body.find("run_canonical_full_stack(")
    ok = integrity > 0 and canonical > integrity
    return AssessmentRow(
        "C2-HTTP-PREFLIGHT-BEFORE-CANONICAL",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        f"integrity_at={integrity}; canonical_at={canonical}",
    )


def _check_dashboard_partial() -> AssessmentRow:
    rows = {r.boundary_id: r for r in ingress_trust_matrix()}
    dash = rows.get("orch-dashboard-full-stack")
    if dash is None:
        return AssessmentRow(
            "C3-DASHBOARD-PARTIAL-PRESERVED",
            AssessmentCheck.FAILED,
            "missing-dashboard-row",
        )
    ok = dash.status is EnforcementStatus.PARTIAL
    return AssessmentRow(
        "C3-DASHBOARD-PARTIAL-PRESERVED",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        f"status={dash.status.value}",
    )


def _check_w10_gates() -> tuple[AssessmentRow, int, bool]:
    report = run_wave10_integration_gate()
    findings: list[str] = []
    gates = report.gates
    if len(gates) != EXPECTED_W10_GATE_COUNT:
        findings.append(f"gate-count:{len(gates)}!={EXPECTED_W10_GATE_COUNT}")
    ids = [g.gate_id for g in gates]
    if len(set(ids)) != len(ids):
        findings.append("duplicate-gate-ids")
    for g in gates:
        if not g.verifier_ref.strip():
            findings.append(f"missing-verifier-ref:{g.gate_id}")
        if g.result not in (GateResult.PASSED, GateResult.FAILED, GateResult.SLICE_ONLY):
            findings.append(f"invalid-result:{g.gate_id}:{g.result}")
    ok = not findings
    row = AssessmentRow(
        "C4-W10-GATE-EVIDENCE-SEMANTICS",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        f"gates={len(gates)}; integration_passed={report.integration_gate_passed}",
    )
    return row, len(gates), report.integration_gate_passed


def _check_w03_w08_linkage() -> AssessmentRow:
    ledger = json.loads(WAVE_LEDGER.read_text(encoding="utf-8"))
    w03 = ledger["work_packages"]["R1-W03"]
    w08 = ledger["work_packages"]["R1-W08"]
    w03_vs = w03.get("verification_status", "")
    w08_vs = w08.get("verification_status", "")
    falsely_closed = w03_vs == "INDEPENDENTLY_VERIFIED" or w08_vs == "INDEPENDENTLY_VERIFIED"
    note_ok = "W03" in w08.get("verification_note", "")
    evidence_ok = bool(w03.get("verification_evidence"))
    matrix_rows = {r.boundary_id for r in ingress_trust_matrix()}
    boundaries_ok = set(W08_W03_BOUNDARY_IDS).issubset(matrix_rows)
    ok = not falsely_closed and note_ok and evidence_ok and boundaries_ok
    return AssessmentRow(
        "C5-W03-LINKED-W08-NOT-CLOSED",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        f"w03_vs={w03_vs}; w08_vs={w08_vs}; boundaries_identified={boundaries_ok}",
    )


def _check_work_package_reconciliation() -> tuple[AssessmentRow, tuple[str, ...]]:
    ledger = json.loads(WAVE_LEDGER.read_text(encoding="utf-8"))
    packages = ledger["work_packages"]
    incomplete: list[str] = []
    findings: list[str] = []
    for i in range(1, 11):
        key = f"R1-W{i:02d}"
        wp = packages.get(key)
        if wp is None:
            findings.append(f"missing:{key}")
            continue
        vs = wp.get("verification_status", "NOT_VERIFIED")
        if vs in ("PARTIALLY_VERIFIED", "NOT_VERIFIED"):
            incomplete.append(f"{key}:{vs}")
        if not wp.get("verification_evidence") and vs not in ("NOT_VERIFIED",):
            if key not in ("R1-W01", "R1-W02"):
                findings.append(f"missing-evidence:{key}")
    ok = len(packages) == 10 and not findings
    row = AssessmentRow(
        "C6-WORK-PACKAGE-RECONCILIATION",
        AssessmentCheck.PASSED if ok else AssessmentCheck.FAILED,
        f"incomplete={','.join(incomplete) or 'none'}",
    )
    return row, tuple(incomplete)


def _next_dependency_advisory(incomplete: tuple[str, ...]) -> AssessmentRow:
    """Semantic-preservation and ingress parity remain open before governed conformance."""
    priority = [
        "R1-W07:PARTIALLY_VERIFIED",
        "R1-W08:PARTIALLY_VERIFIED",
        "R1-W03:PARTIALLY_VERIFIED",
        "R1-W09:PARTIALLY_VERIFIED",
    ]
    ranked = [p for p in priority if p in incomplete]
    next_dep = ranked[0] if ranked else (incomplete[0] if incomplete else "none")
    return AssessmentRow(
        "C7-NEXT-INCOMPLETE-DEPENDENCY",
        AssessmentCheck.ADVISORY,
        f"recommended_next={next_dep}; do_not_expand_w08_matrix_by_default",
    )


def run_r5_w03_w10_closure_assessment() -> R5W03W10ClosureAssessment:
    findings: list[str] = []
    checks: list[AssessmentRow] = []

    c1 = _check_w03_iv()
    checks.append(c1)
    if c1.result is AssessmentCheck.FAILED:
        findings.append(c1.check_id)

    c2 = _check_http_preflight_order()
    checks.append(c2)
    if c2.result is AssessmentCheck.FAILED:
        findings.append(c2.check_id)

    c3 = _check_dashboard_partial()
    checks.append(c3)
    if c3.result is AssessmentCheck.FAILED:
        findings.append(c3.check_id)

    c4, gate_count, w10_ok = _check_w10_gates()
    checks.append(c4)
    if c4.result is AssessmentCheck.FAILED:
        findings.append(c4.check_id)

    c5 = _check_w03_w08_linkage()
    checks.append(c5)
    if c5.result is AssessmentCheck.FAILED:
        findings.append(c5.check_id)

    c6, incomplete = _check_work_package_reconciliation()
    checks.append(c6)
    if c6.result is AssessmentCheck.FAILED:
        findings.append(c6.check_id)

    c7 = _next_dependency_advisory(incomplete)
    checks.append(c7)

    w03_report = run_w03_revision_integrity_verification()
    critical_failed = any(c.result is AssessmentCheck.FAILED for c in checks)

    return R5W03W10ClosureAssessment(
        verifier_id=INDEPENDENT_VERIFIER_R5_CLOSURE,
        checks=tuple(checks),
        w03_iv_passed=w03_report.passed,
        w10_gate_count=gate_count,
        w10_integration_passed=w10_ok,
        dashboard_ingress_status=c3.detail,
        r1_w03_closure_claimed=False,
        r1_w08_closure_claimed=False,
        w08_universal_closure_claimed=False,
        next_incomplete_dependencies=incomplete,
        assessment_passed=not critical_failed and w03_report.passed and w10_ok,
        findings=tuple(findings),
    )


def write_r5_closure_assessment_evidence(
    path: Path,
    report: R5W03W10ClosureAssessment,
) -> None:
    payload = {
        "schema": "tiannara.cp067.r5_w03_w10_closure_assessment",
        "verifier_id": report.verifier_id,
        "checks": [
            {"check_id": c.check_id, "result": c.result.value, "detail": c.detail}
            for c in report.checks
        ],
        "w03_iv_passed": report.w03_iv_passed,
        "w10_gate_count": report.w10_gate_count,
        "w10_integration_passed": report.w10_integration_passed,
        "dashboard_ingress_status": report.dashboard_ingress_status,
        "r1_w03_closure_claimed": report.r1_w03_closure_claimed,
        "r1_w08_closure_claimed": report.r1_w08_closure_claimed,
        "w08_universal_closure_claimed": report.w08_universal_closure_claimed,
        "next_incomplete_dependencies": list(report.next_incomplete_dependencies),
        "assessment_passed": report.assessment_passed,
        "findings": list(report.findings),
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
