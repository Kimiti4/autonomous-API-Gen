"""CP067 R1-W07 ADR-R1-03 bridge semantic evidence."""

from __future__ import annotations

import json
from pathlib import Path

from certification.isr_independent_verification.w07_bridge_semantic_evidence import (
    INDEPENDENT_VERIFIER_W07,
    run_w07_bridge_semantic_evidence,
    write_w07_bridge_evidence,
)


def test_w07_bridge_semantic_evidence_passes():
    report = run_w07_bridge_semantic_evidence()
    assert report.verifier_id == INDEPENDENT_VERIFIER_W07
    assert report.contracts_complete
    assert report.b04_oracle_passed
    assert report.b07_fail_closed_enforced
    assert report.unsupported_bridges_untrusted
    assert report.passed, report.findings


def test_w07_evidence_artifact_roundtrip():
    path = Path("release/evidence/cp067_w07_bridge_semantic_evidence_report.json")
    report = run_w07_bridge_semantic_evidence()
    write_w07_bridge_evidence(path, report)
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "tiannara.cp067.w07_bridge_semantic_evidence"
    assert payload["passed"] is True
    assert set(payload["adr_r1_03_minimum_set"]) == {"B-03", "B-04", "B-07", "B-08", "B-09"}
