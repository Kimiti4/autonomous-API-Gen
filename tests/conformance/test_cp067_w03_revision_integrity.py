"""CP067 R1-W03 revision integrity (W08 ingress scope)."""

from __future__ import annotations

import json
from pathlib import Path

from certification.isr_independent_verification.w03_revision_integrity_verification import (
    INDEPENDENT_VERIFIER_W03,
    run_w03_revision_integrity_verification,
    write_w03_revision_integrity_evidence,
)


def test_w03_revision_integrity_verification_passes():
    report = run_w03_revision_integrity_verification()
    assert report.verifier_id == INDEPENDENT_VERIFIER_W03
    assert report.passed, report.findings


def test_w03_evidence_artifact():
    path = Path("release/evidence/cp067_w03_revision_integrity_report.json")
    report = run_w03_revision_integrity_verification()
    write_w03_revision_integrity_evidence(path, report)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert len(payload["w08_w03_boundaries"]) == 3
