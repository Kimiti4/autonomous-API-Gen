"""Factory -> EvidenceLedger adapter (Phase 18 evidence sink, Phase 19 wiring).

A ``SoftwareFactory.run`` report is a multi-outcome compilation/verification
result (one outcome per materialized backend in ``plan_all`` mode). The
``EvidenceLedger`` protocol is per-backend (``CertificationEvidence`` carries a
single ``backend_name`` / ``genome_id`` / ``fitness``). This adapter maps each
``VerificationOutcome`` onto its own ``CertificationEvidence`` so a factory run
emits one tamper-evident ledger record per backend -- the durable record that
Phase 20/38 learning and Phase 31 certification consume.

This is the missing link that closes the Phase-18 ``evidence_sink`` seam:
``SoftwareFactory(evidence_sink=make_factory_evidence_sink(ledger))`` makes every
``factory.run(...)`` append durable, hash-chained evidence.
"""
from __future__ import annotations

from typing import Any

from tiannara.domain.models.evidence import (
    CertificationEvidence,
    TestRunResult,
    Verdict,
)
from tiannara.domain.models.fitness import FitnessVector

#: The plan_id from a compiled run is the closest stable identifier available;
#: it is used as the evidence record's genome_id (a true evolutionary genome is
#: not present in the compile path). Documented as a deliberate surrogate.
_PLAN_AS_GENOME = True


def factory_report_to_certification_evidence(report: Any) -> list[CertificationEvidence]:
    """Map a ``SoftwareFactoryReport`` to one ``CertificationEvidence`` per outcome."""
    outcomes = getattr(report, "verification_outcomes", ()) or ()
    isr_hash = getattr(report, "isr_hash", "")
    plan_id = getattr(report, "plan_id", "") or ""
    fitness = getattr(report, "fitness", None)
    fitness_metrics = dict(getattr(fitness, "metrics", {}) or {}) if fitness is not None else {}

    # Prefer the materialized system slug as the project_id; fall back to the
    # statement hash so the record is always attributable.
    materialization = getattr(report, "materialization", None)
    bundles = getattr(materialization, "bundles", ()) or ()
    project_id = ""
    if bundles:
        project_id = getattr(bundles[0], "project_id", "") or ""
    if not project_id:
        project_id = getattr(report, "statement_hash", "") or "unknown"

    fitness_vector = FitnessVector(metrics=fitness_metrics)

    records: list[CertificationEvidence] = []
    for outcome in outcomes:
        test_result = getattr(outcome, "test_result", None)
        test_run = test_result if isinstance(test_result, TestRunResult) else None
        compiled_ok = bool(getattr(outcome, "ok", False))
        records.append(
            CertificationEvidence(
                project_id=project_id,
                isr_hash=isr_hash,
                # Pre-evolution genome marker: the ISR *is* the design under
                # evaluation. The ``pre-evolution:`` prefix keeps records from
                # the compile path distinguishable from Evolutionary Engine
                # outputs and migratable once real genomes exist.
                genome_id=f"pre-evolution:{isr_hash[:16]}",
                backend_name=getattr(outcome, "bundle_backend_id", "") or "",
                compilation_success=compiled_ok,
                test_run=test_run,
                fitness=fitness_vector,
                verdict=Verdict.PASS if compiled_ok else Verdict.FAIL,
                error=None,
            )
        )
    return records


def make_factory_evidence_sink(ledger: Any) -> Any:
    """Return an ``evidence_sink`` callable for ``SoftwareFactory``.

    The factory's ``run`` invokes ``evidence_sink(report)`` with the final report
    (on both success and failure paths, before it raises). The sink appends one
    hashed, tamper-evident record per backend outcome. Sink failures are already
    swallowed by the factory's ``try/except``; this adapter does not swallow them
    itself so test doubles can observe errors.
    """
    def sink(report: Any) -> None:
        for record in factory_report_to_certification_evidence(report):
            ledger.append(record)
    return sink
