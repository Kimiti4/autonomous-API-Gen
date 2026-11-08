"""CP067-R4 independent verification entrypoint."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.isr_independent_verification.plan_binding_oracle import (
    run_plan_binding_oracle,
)
from certification.payroll.candidate_fixture import payroll_isr_revision
from isr.core.revision import ISRRevision


@dataclass(frozen=True)
class Wave2IndependentReport:
    workload: str
    revision_id: str
    w04_passed: bool
    w05_passed: bool
    w04_findings: tuple[str, ...]
    w05_findings: tuple[str, ...]


def _w04_passed(report) -> bool:
    return (
        report.isr_digest_independent_match
        and report.plan_digest_independent_match
        and report.binding_fields_complete
        and report.stale_record_rejected
        and report.tampered_isr_rejected
        and not report.findings
    )


def _w05_passed(report) -> bool:
    return all(
        (
            report.isr_revision_orchestration_ok,
            report.implir_orchestration_blocked,
            report.engisr_without_lineage_blocked,
            report.engisr_with_lineage_orchestration_ok,
            report.publication_implir_blocked,
            report.publication_engisr_blocked,
            report.non_authoritative_marker_ok,
        )
    ) and not report.findings


def run_wave2_independent_verification(
    revision: ISRRevision | None = None,
    *,
    workload_id: str = "payroll-human",
) -> Wave2IndependentReport:
    revision = revision or payroll_isr_revision()
    w04 = run_plan_binding_oracle(revision)
    w05 = run_implir_ingress_oracle()
    return Wave2IndependentReport(
        workload=workload_id,
        revision_id=revision.revision_id,
        w04_passed=_w04_passed(w04),
        w05_passed=_w05_passed(w05),
        w04_findings=w04.findings,
        w05_findings=w05.findings,
    )


def write_wave2_evidence(path: Path, report: Wave2IndependentReport) -> None:
    payload = {
        "schema": "tiannara.cp067.wave2_independent_verification",
        "w04_passed": report.w04_passed,
        "w05_passed": report.w05_passed,
        "workload": report.workload,
        "revision_id": report.revision_id,
        "w04_findings": list(report.w04_findings),
        "w05_findings": list(report.w05_findings),
        "p0_closure": False,
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
