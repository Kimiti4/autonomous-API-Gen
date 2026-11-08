"""Independent verification — W04 plan binding and W05 ImplIR ingress (CP067-R4-IV)."""

from __future__ import annotations

from pathlib import Path

import pytest

from certification.isr_independent_verification import (
    run_wave2_independent_verification,
    write_wave2_evidence,
)
from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.isr_independent_verification.plan_binding_oracle import (
    run_plan_binding_oracle,
)
from certification.orchestration.authority import run_canonical_full_stack
from certification.payroll.candidate_fixture import payroll_isr_revision


def test_independent_w04_payroll_oracle():
    rev = payroll_isr_revision()
    report = run_plan_binding_oracle(rev)
    assert report.isr_digest_independent_match
    assert report.plan_digest_independent_match
    assert report.stale_record_rejected
    assert report.tampered_isr_rejected
    assert not report.findings


def test_independent_w05_policy_matrix():
    report = run_implir_ingress_oracle()
    assert report.implir_orchestration_blocked
    assert report.publication_implir_blocked
    assert not report.findings


def test_wave2_combined_report():
    summary = run_wave2_independent_verification()
    assert summary.w04_passed
    assert summary.w05_passed


def test_orchestration_path_emits_binding_under_iv(tmp_path):
    """Black-box: governed orchestration + independent oracle agree on payroll."""
    report = run_canonical_full_stack(
        "payroll",
        evidence_registry_path=str(tmp_path / "tev.jsonl"),
        governance_store_path=str(tmp_path / "gov"),
        orchestration_store_path=str(tmp_path / "orun"),
    )
    iv = run_wave2_independent_verification()
    assert iv.w04_passed
    assert report.plan_binding_digest
    assert len(report.plan_binding_digest) == 64


def test_evidence_artifact_written(tmp_path: Path):
    rep = run_wave2_independent_verification()
    out = tmp_path / "wave2-iv.json"
    write_wave2_evidence(out, rep)
    assert rep.w04_passed and rep.w05_passed
    loaded = out.read_text(encoding="utf-8")
    assert '"w04_passed": true' in loaded
