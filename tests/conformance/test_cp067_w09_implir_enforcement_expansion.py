"""CP067 R1-W09 ImplIR enforcement expansion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from certification.isr_independent_verification.w09_implir_enforcement_expansion import (
    INDEPENDENT_VERIFIER_W09,
    run_w09_implir_enforcement_expansion,
    write_w09_implir_evidence,
)
from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    IsrIngressAuthority,
    assert_trusted_maintenance_ingress,
)


def test_w09_implir_enforcement_expansion_passes():
    report = run_w09_implir_enforcement_expansion()
    assert report.verifier_id == INDEPENDENT_VERIFIER_W09
    assert report.passed, report.findings


def test_w09_evidence_artifact():
    path = Path("release/evidence/cp067_w09_implir_enforcement_expansion_report.json")
    report = run_w09_implir_enforcement_expansion()
    write_w09_implir_evidence(path, report)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert len(payload["expanded_boundaries"]) == 6


def test_maintenance_production_write_blocks_implir():
    with pytest.raises(ImplirIngressBlocked, match="maintenance-implir"):
        assert_trusted_maintenance_ingress(
            IsrIngressAuthority.IMPLEMENTATION_IR.value,
            governed_lineage_ref="isr.core.revision:x",
            production_write_requested=True,
        )
