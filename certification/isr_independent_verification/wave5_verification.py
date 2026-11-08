"""CP067-R5 multi-workload and integration verification (W04/W08/W10)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.isr_independent_verification.plan_binding_oracle import (
    run_plan_binding_oracle,
)
from certification.isr_independent_verification.wave2_verification import _w04_passed, _w05_passed
from certification.orchestration.ingress_trust_matrix import ingress_trust_matrix
from certification.orchestration.workload_registry import ALL_WORKLOAD_IDS, get_workload_spec

INDEPENDENT_VERIFIER_W10 = "certification.isr_independent_verification.wave5_integration_gate.v1"

R5_MULTI_WORKLOAD_SLICE = ("payroll", "orders", "appointments")


@dataclass(frozen=True)
class WorkloadPlanBindingRow:
    workload_id: str
    revision_id: str
    w04_passed: bool
    findings: tuple[str, ...]


@dataclass(frozen=True)
class Wave5IndependentReport:
    verifier_id: str
    workload_rows: tuple[WorkloadPlanBindingRow, ...]
    w05_policy_passed: bool
    w08_matrix_entries: int
    w10_integration_passed: bool
    cp068_admission: str
    p0_closure: bool
    findings: tuple[str, ...]


def run_multi_workload_plan_binding(
    workload_ids: tuple[str, ...] = R5_MULTI_WORKLOAD_SLICE,
) -> tuple[WorkloadPlanBindingRow, ...]:
    rows: list[WorkloadPlanBindingRow] = []
    for wid in workload_ids:
        if wid not in ALL_WORKLOAD_IDS:
            rows.append(
                WorkloadPlanBindingRow(
                    workload_id=wid,
                    revision_id="",
                    w04_passed=False,
                    findings=(f"unknown-workload:{wid}",),
                )
            )
            continue
        spec = get_workload_spec(wid)
        revision = spec.revision_fn()
        oracle = run_plan_binding_oracle(revision)
        rows.append(
            WorkloadPlanBindingRow(
                workload_id=wid,
                revision_id=revision.revision_id,
                w04_passed=_w04_passed(oracle),
                findings=oracle.findings,
            )
        )
    return tuple(rows)


def run_wave5_independent_verification(
    workload_ids: tuple[str, ...] = R5_MULTI_WORKLOAD_SLICE,
) -> Wave5IndependentReport:
    findings: list[str] = []
    workload_rows = run_multi_workload_plan_binding(workload_ids)
    for row in workload_rows:
        if not row.w04_passed:
            findings.append(f"w04-failed:{row.workload_id}")

    w05 = run_implir_ingress_oracle()
    w05_ok = _w05_passed(w05)
    if not w05_ok:
        findings.extend(f"w05:{x}" for x in w05.findings)

    w08_count = len(ingress_trust_matrix())
    w10_ok = all(r.w04_passed for r in workload_rows) and w05_ok

    return Wave5IndependentReport(
        verifier_id=INDEPENDENT_VERIFIER_W10,
        workload_rows=workload_rows,
        w05_policy_passed=w05_ok,
        w08_matrix_entries=w08_count,
        w10_integration_passed=w10_ok,
        cp068_admission="CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
        p0_closure=False,
        findings=tuple(findings),
    )


def write_wave5_evidence(path: Path, report: Wave5IndependentReport) -> None:
    payload = {
        "schema": "tiannara.cp067.wave5_independent_verification",
        "verifier_id": report.verifier_id,
        "workloads": [
            {
                "workload_id": r.workload_id,
                "revision_id": r.revision_id,
                "w04_passed": r.w04_passed,
                "findings": list(r.findings),
            }
            for r in report.workload_rows
        ],
        "w05_policy_passed": report.w05_policy_passed,
        "w08_matrix_entries": report.w08_matrix_entries,
        "w10_integration_passed": report.w10_integration_passed,
        "cp068_admission": report.cp068_admission,
        "p0_closure": report.p0_closure,
        "findings": list(report.findings),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
