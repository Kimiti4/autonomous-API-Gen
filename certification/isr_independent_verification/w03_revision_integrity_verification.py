"""CP067 R1-W03 — revision immutability / integrity IV (W08 ingress scope)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from certification.isr_independent_verification.wave5_verification import (
    R5_MULTI_WORKLOAD_SLICE,
)
from certification.orchestration.ingress_revision_integrity_gate import (
    W08_W03_BOUNDARY_IDS,
    assert_w08_ingress_revision_integrity,
)
from certification.orchestration.workload_registry import get_workload_spec
from isr.core.digest_verification import DigestVerificationError
from isr.core.revision_integrity import assert_revision_integrity_at_boundary

INDEPENDENT_VERIFIER_W03 = (
    "certification.isr_independent_verification.w03_revision_integrity_verification.v1"
)


@dataclass(frozen=True)
class W03RevisionIntegrityReport:
    verifier_id: str
    workload_slice: tuple[str, ...]
    w08_w03_boundaries: tuple[str, ...]
    slice_integrity_passed: bool
    tamper_detection_passed: bool
    passed: bool
    findings: tuple[str, ...]


def run_w03_revision_integrity_verification() -> W03RevisionIntegrityReport:
    findings: list[str] = []
    slice_ok = True
    for wid in R5_MULTI_WORKLOAD_SLICE:
        try:
            rev = get_workload_spec(wid).revision_fn()
            assert_w08_ingress_revision_integrity(
                rev,
                boundary_id="orchestration-authority",
            )
        except Exception as exc:
            findings.append(f"workload-{wid}:{exc}")
            slice_ok = False

    tamper_ok = False
    try:
        rev = get_workload_spec(R5_MULTI_WORKLOAD_SLICE[0]).revision_fn()
        tampered = rev.model_copy(update={"content_hash": "0" * 64})
        try:
            assert_revision_integrity_at_boundary(tampered)
            findings.append("tamper-should-fail")
        except DigestVerificationError:
            tamper_ok = True
    except Exception as exc:
        findings.append(f"tamper-setup:{exc}")

    passed = slice_ok and tamper_ok
    return W03RevisionIntegrityReport(
        verifier_id=INDEPENDENT_VERIFIER_W03,
        workload_slice=R5_MULTI_WORKLOAD_SLICE,
        w08_w03_boundaries=W08_W03_BOUNDARY_IDS,
        slice_integrity_passed=slice_ok,
        tamper_detection_passed=tamper_ok,
        passed=passed,
        findings=tuple(findings),
    )


def write_w03_revision_integrity_evidence(
    path: Path,
    report: W03RevisionIntegrityReport,
) -> None:
    payload = {
        "schema": "tiannara.cp067.w03_revision_integrity_verification",
        "verifier_id": report.verifier_id,
        "workload_slice": list(report.workload_slice),
        "w08_w03_boundaries": list(report.w08_w03_boundaries),
        "slice_integrity_passed": report.slice_integrity_passed,
        "tamper_detection_passed": report.tamper_detection_passed,
        "passed": report.passed,
        "findings": list(report.findings),
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
