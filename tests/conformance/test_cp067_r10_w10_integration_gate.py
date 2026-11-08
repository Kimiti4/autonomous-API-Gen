"""CP067-R10 W10 independent integration gate."""

from __future__ import annotations

import json
from pathlib import Path

from certification.isr_independent_verification.wave10_integration_gate import (
    GateResult,
    INDEPENDENT_VERIFIER_W10_GATE,
    run_wave10_integration_gate,
    write_wave10_integration_evidence,
)


def test_wave10_integration_gate_passes_on_repo_slice():
    report = run_wave10_integration_gate()
    assert report.verifier_id == INDEPENDENT_VERIFIER_W10_GATE
    assert report.integration_gate_passed, report.findings
    assert report.governed_p0_all_closed_scoped
    assert report.cp068_admission == "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY"
    failed = [g for g in report.gates if g.result is GateResult.FAILED]
    assert not failed, [(g.gate_id, g.findings) for g in failed]


def test_wave10_integration_evidence_artifact():
    path = Path("release/evidence/cp067_r10_w10_integration_gate_report.json")
    report = run_wave10_integration_gate()
    write_wave10_integration_evidence(path, report)
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "tiannara.cp067.w10_integration_gate"
    assert payload["integration_gate_passed"] is True
    assert len(payload["gates"]) >= 10
