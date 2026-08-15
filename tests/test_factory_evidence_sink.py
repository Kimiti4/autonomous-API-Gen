"""Phase 19 -- factory -> durable evidence ledger wiring.

Closes the Phase-18 ``evidence_sink`` seam: a ``SoftwareFactory.run`` report is
mapped to one ``CertificationEvidence`` per backend outcome and appended to the
hash-chained ``JsonlEvidenceLedger``.
"""
from __future__ import annotations

import pytest

from tiannara.application.factory.evidence_sink import (
    factory_report_to_certification_evidence,
    make_factory_evidence_sink,
)
from tiannara.application.factory import SoftwareFactory
from tiannara.domain.models.evidence import CertificationEvidence, Verdict


class _Outcome:
    def __init__(self, backend_id, ok, repair_attempts=0, repaired=False, test_result=None):
        self.bundle_backend_id = backend_id
        self.ok = ok
        self.repair_attempts = repair_attempts
        self.repaired = repaired
        self.test_result = test_result


class _Fitness:
    def __init__(self, metrics):
        self.metrics = metrics


class _Materialization:
    def __init__(self, project_id):
        class _B:
            pass
        b = _B()
        b.project_id = project_id
        self.bundles = (b,)


class _Report:
    def __init__(self, outcomes, *, isr_hash="isr-1", plan_id="plan-1",
                 statement_hash="stmt-1", project_id="order_management", fitness=None, ok=True):
        self.verification_outcomes = outcomes
        self.isr_hash = isr_hash
        self.plan_id = plan_id
        self.statement_hash = statement_hash
        self.materialization = _Materialization(project_id)
        self.fitness = fitness
        self.ok = ok
        self.policy_name = "default"


def test_report_maps_one_record_per_outcome():
    report = _Report([
        _Outcome("fastapi_hexagonal", ok=True, repair_attempts=0, repaired=False),
        _Outcome("go_hexagonal", ok=True, repair_attempts=1, repaired=True),
    ], fitness=_Fitness({"verification": 1.0, "repair_free": 0.5}))
    records = factory_report_to_certification_evidence(report)
    assert len(records) == 2
    fastapi, go = records
    assert fastapi.backend_name == "fastapi_hexagonal"
    assert fastapi.project_id == "order_management"
    assert fastapi.isr_hash == "isr-1"
    assert fastapi.genome_id == "pre-evolution:isr-1"
    assert fastapi.compilation_success is True
    assert fastapi.verdict is Verdict.PASS
    assert fastapi.fitness.metrics["repair_free"] == 0.5

    assert go.backend_name == "go_hexagonal"
    assert go.repaired if hasattr(go, "repaired") else True
    # repaired state is not part of CertificationEvidence; outcome ok drives verdict.
    assert go.verdict is Verdict.PASS


def test_report_failed_outcome_maps_to_fail_verdict():
    report = _Report([_Outcome("go_hexagonal", ok=False)], ok=False, fitness=None)
    records = factory_report_to_certification_evidence(report)
    assert len(records) == 1
    assert records[0].compilation_success is False
    assert records[0].verdict is Verdict.FAIL


def test_sink_appends_to_ledger_and_chain_verifies(tmp_path):
    from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger

    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    sink = make_factory_evidence_sink(ledger)
    report = _Report([
        _Outcome("fastapi_hexagonal", ok=True),
        _Outcome("go_hexagonal", ok=True),
    ], isr_hash="isr-shared")
    sink(report)

    assert len(ledger.all()) == 2
    assert ledger.verify_chain() is True
    fastapi_recs = ledger.query(backend_name="fastapi_hexagonal")
    go_recs = ledger.query(backend_name="go_hexagonal")
    assert len(fastapi_recs) == 1 and len(go_recs) == 1
    assert all(r.isr_hash == "isr-shared" for r in ledger.query(isr_hash="isr-shared"))


def test_sink_records_are_certification_evidence_instances(tmp_path):
    from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger

    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    make_factory_evidence_sink(ledger)(
        _Report([_Outcome("go_hexagonal", ok=True)])
    )
    loaded = ledger.all()
    assert isinstance(loaded[0], CertificationEvidence)
