"""CP067-R5 supplement — W03 closure assessment and W10 verification."""

from __future__ import annotations

import json
from pathlib import Path

from certification.isr_independent_verification.r5_w03_w10_closure_assessment import (
    EXPECTED_W10_GATE_COUNT,
    INDEPENDENT_VERIFIER_R5_CLOSURE,
    AssessmentCheck,
    run_r5_w03_w10_closure_assessment,
    write_r5_closure_assessment_evidence,
)


def test_r5_w03_w10_closure_assessment_passes():
    report = run_r5_w03_w10_closure_assessment()
    assert report.verifier_id == INDEPENDENT_VERIFIER_R5_CLOSURE
    assert report.assessment_passed, report.findings
    assert report.w10_gate_count == EXPECTED_W10_GATE_COUNT
    assert report.r1_w03_closure_claimed is False
    assert report.r1_w08_closure_claimed is False
    assert report.w08_universal_closure_claimed is False
    assert "R1-W07" in "".join(report.next_incomplete_dependencies)
    assert "R1-W08" in "".join(report.next_incomplete_dependencies)
    failed = [c for c in report.checks if c.result is AssessmentCheck.FAILED]
    assert not failed, [(c.check_id, c.detail) for c in failed]


def test_r5_closure_assessment_evidence_artifact():
    path = Path("release/evidence/cp067_r5_w03_closure_w10_assessment_report.json")
    report = run_r5_w03_w10_closure_assessment()
    write_r5_closure_assessment_evidence(path, report)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["assessment_passed"] is True
    assert payload["r1_w03_closure_claimed"] is False
    assert len(payload["checks"]) == 7
