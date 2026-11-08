"""CP067 — read-only ISR-family canonicality audit (no remediation in this module)."""
from __future__ import annotations

from certification.evidence_graph.cp067_isr_canonicality_audit import (
    BridgeSemantics,
    GapSeverity,
    run_cp067_readonly_audit,
    recompute_payroll_hash_slice,
)


def test_cp067_inventory_lists_non_interchangeable_families():
    report = run_cp067_readonly_audit()
    assert len(report.families) >= 5
    paths = {f.module_path for f in report.families}
    assert "isr.core.revision.ISRRevision" in str(paths)
    assert "constitutional_architecture.isr.model" in str(paths)


def test_cp067_bridges_do_not_claim_universal_lossless():
    report = run_cp067_readonly_audit()
    lossy = [b for b in report.bridges if b.semantics is BridgeSemantics.LOSSY]
    assert lossy
    lowering = next(b for b in report.bridges if b.bridge_id == "isr-to-compilation-plan")
    assert lowering.semantics is BridgeSemantics.LOSSY
    assert lowering.hash_preserved is False


def test_cp067_gap_register_includes_dual_hash_p0():
    report = run_cp067_readonly_audit()
    dual = next(g for g in report.gaps if g.gap_id == "dual-hash-algorithms")
    assert dual.severity is GapSeverity.P0
    assert dual.remediation_status == "OPEN"


def test_payroll_isr_hash_recomputation_slice():
    report = run_cp067_readonly_audit()
    assert report.payroll_human_hash_ok
    assert report.payroll_synth_hash_ok
    assert report.payroll_human_synth_different


def test_payroll_hash_pairs_expose_stored_vs_recomputed():
    pairs = recompute_payroll_hash_slice()
    assert len(pairs) == 2
    assert all(p.matches for p in pairs)
    assert pairs[0].stored != pairs[1].stored
