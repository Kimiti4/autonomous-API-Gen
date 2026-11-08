"""Independent verifier lane — must not rely on generator self-assertions alone."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from certification.isr_independent_verification import (
    INDEPENDENT_VERIFIER_ID,
    run_independent_digest_verification,
)
from certification.payroll.candidate_fixture import payroll_isr_revision


def test_independent_oracle_payroll_human_isr():
    revision = payroll_isr_revision()
    report = run_independent_digest_verification(revision)
    assert report.verifier_id == INDEPENDENT_VERIFIER_ID
    assert report.tier_a_f01_passed
    assert report.tier_b_f04_passed
    assert report.tier_b_f05_passed
    assert report.payroll_fixture_passed
    assert report.adversarial_cross_domain_passed
    assert not report.findings


def test_independent_oracle_writes_evidence_artifact(tmp_path: Path, monkeypatch):
    revision = payroll_isr_revision()
    report = run_independent_digest_verification(revision)
    payload = {
        "verifier_id": report.verifier_id,
        "tier_a_f01_passed": report.tier_a_f01_passed,
        "tier_b_f04_passed": report.tier_b_f04_passed,
        "tier_b_f05_passed": report.tier_b_f05_passed,
        "payroll_fixture_passed": report.payroll_fixture_passed,
        "adversarial_cross_domain_passed": report.adversarial_cross_domain_passed,
        "findings": list(report.findings),
        "isr_revision_id": revision.revision_id,
        "isr_content_hash": revision.content_hash,
    }
    out = tmp_path / "iv-report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text())
    assert loaded["tier_a_f01_passed"] is True


def test_independent_oracle_rejects_tampered_hash():
    from isr.core.graph import ISRGraph, Node, NodeType
    from isr.core.identity import Provenance
    from isr.core.revision import ISRRevision

    rev = payroll_isr_revision()
    tampered = rev.model_copy(update={"content_hash": "f" * 64})
    report = run_independent_digest_verification(tampered)
    assert not report.tier_a_f01_passed
    assert any("tier-a" in f for f in report.findings)
