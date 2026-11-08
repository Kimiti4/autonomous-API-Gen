"""P0 closure harness — independent proof aggregator (honest stages)."""

from __future__ import annotations

from certification.isr_independent_verification.p0_closure_harness import (
    P0ClosureStage,
    run_p0_closure_harness,
)


def test_p0_harness_runs_all_five_findings():
    rows = run_p0_closure_harness()
    assert len(rows) == 5
    ids = {r.finding_id for r in rows}
    assert ids == {
        "CP067-ISR-001",
        "CP067-ISR-002",
        "CP067-ISR-003",
        "CP067-ISR-004",
        "CP067-ISR-008",
    }


def test_p0_001_003_008_closed_in_governed_scope():
    by_id = {r.finding_id: r for r in run_p0_closure_harness()}
    assert by_id["CP067-ISR-001"].stage in (
        P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED,
        P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED,
    )
    assert by_id["CP067-ISR-003"].stage == P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED
    assert by_id["CP067-ISR-008"].stage == P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED


def test_p0_002_obligation_verifier_closed_in_governed_scope():
    by_id = {r.finding_id: r for r in run_p0_closure_harness()}
    assert by_id["CP067-ISR-002"].stage == P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED
    assert not by_id["CP067-ISR-002"].blockers


def test_p0_004_remains_partial():
    by_id = {r.finding_id: r for r in run_p0_closure_harness()}
    assert by_id["CP067-ISR-004"].stage == P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED
    assert by_id["CP067-ISR-004"].blockers


def test_cp067_isr002_supplement_ratified_on_disk():
    import json
    from pathlib import Path

    path = Path("release/evidence/cp067_isr002_supplement_ratification_2026-11-08.json")
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "RATIFIED"
    assert payload["finding_decision"]["finding_id"] == "CP067-ISR-002"
    assert (
        payload["finding_decision"]["governed_status_after_supplement"]
        == "CLOSED_SCOPED"
    )


def test_p0_closure_evidence_on_disk_governance_linked():
    import json
    from pathlib import Path

    proof = Path("release/evidence/cp067_p0_closure_independent_proof_report.json")
    human = Path("release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json")
    assert proof.is_file()
    assert human.is_file()
    payload = json.loads(proof.read_text(encoding="utf-8"))
    ratification = json.loads(human.read_text(encoding="utf-8"))
    assert payload["governance_approval"] is True
    assert (
        payload["governance_ratification_evidence"]
        == "release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json"
    )
    assert ratification["status"] == "RATIFIED"
    assert payload["verifier_id"] == (
        "certification.isr_independent_verification.p0_closure_harness.v1"
    )
