"""Phase 19 -- JsonlEvidenceLedger read/query + factory->ledger integration."""
from __future__ import annotations

from tiannara.application.factory.evidence_sink import make_factory_evidence_sink
from tiannara.domain.models.evidence import CertificationEvidence, Verdict
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger


def _ev(project_id, isr_hash, backend, verdict_ok):
    return CertificationEvidence(
        project_id=project_id,
        isr_hash=isr_hash,
        genome_id="plan-1",
        backend_name=backend,
        compilation_success=verdict_ok,
        verdict=Verdict.PASS if verdict_ok else Verdict.FAIL,
    )


def test_query_filters_by_keys(tmp_path):
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    ledger.append(_ev("p1", "h1", "fastapi", True))
    ledger.append(_ev("p1", "h2", "go", True))
    ledger.append(_ev("p2", "h3", "go", False))

    assert len(ledger.query()) == 3
    assert len(ledger.query(isr_hash="h1")) == 1
    assert len(ledger.query(backend_name="go")) == 2
    assert len(ledger.query(project_id="p1")) == 2
    assert len(ledger.query(verdict=Verdict.PASS)) == 2
    assert len(ledger.query(verdict=Verdict.FAIL)) == 1


def test_query_preserves_append_order_and_chain(tmp_path):
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    ledger.append(_ev("p1", "h1", "fastapi", True))
    ledger.append(_ev("p2", "h2", "go", False))
    go_recs = ledger.query(backend_name="go")
    assert go_recs[0].project_id == "p2"
    assert ledger.verify_chain() is True


class _Outcome:
    bundle_backend_id = "stub"
    ok = True
    repair_attempts = 0
    repaired = False
    test_result = None


class _Fitness:
    metrics = {"verification": 1.0, "repair_free": 1.0, "build": 1.0, "scan": 1.0, "test": 1.0}


class _Bundle:
    project_id = "stub"


class _Report:
    statement_hash = "stmt"
    isr_hash = "isr-abc"
    plan_id = "plan-1"
    policy_name = "default"
    verification_outcomes = (_Outcome(),)
    fitness = _Fitness()
    ok = True
    materialization = type("M", (), {"bundles": (_Bundle(),)})()


def test_factory_report_maps_into_durable_ledger(tmp_path):
    """One CertifiedEvidence record per outcome, appended + chain-verified."""
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    make_factory_evidence_sink(ledger)(_Report())

    records = ledger.all()
    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, CertificationEvidence)
    assert rec.backend_name == "stub"
    assert rec.isr_hash == "isr-abc"
    assert rec.genome_id == "pre-evolution:isr-abc"
    assert rec.compilation_success is True
    assert rec.verdict is Verdict.PASS
    assert rec.fitness.metrics["verification"] == 1.0
    assert ledger.verify_chain() is True
    assert ledger.query(backend_name="stub")[0].verdict is Verdict.PASS
    assert ledger.query(isr_hash="isr-abc")[0].project_id == "stub"
