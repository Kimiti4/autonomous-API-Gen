"""Aggregate independently verified obligation evidence into a bounded gate.

This module is the final evidence-assembly boundary: every required obligation
must have exactly one source-bound record and a successful verdict from the
independent evidence verifier. It does not retrieve evidence or claim that
hash integrity proves the truth of a runner's assertion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tiannara.application.compiler.obligation_evidence import ObligationEvidenceVerdict
from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
)


@dataclass(frozen=True)
class ObligationCertificationVerdict:
    """Conservative aggregate result for one exact source graph."""

    disposition: Disposition
    required_obligations: tuple[str, ...]
    passed_obligations: tuple[str, ...]
    blocked_obligations: tuple[str, ...]
    failed_obligations: tuple[str, ...]
    unknown_obligations: tuple[str, ...]
    blockers: tuple[str, ...]
    attestation_ids: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.disposition is Disposition.PASS and not self.blockers


def assemble_obligation_certification(
    evaluations: Iterable[tuple[CompilerObligationRecord, ObligationEvidenceVerdict]],
    *,
    expected_source_graph_hash: str,
    required_obligation_ids: Iterable[str],
) -> ObligationCertificationVerdict:
    """Aggregate verifier results without upgrading any non-PASS state.

    The required ID list comes from the authoritative suite definition, not
    from whichever records happen to be present. Duplicates, missing records,
    stale sources, and contradictory results fail closed.
    """
    required = tuple(sorted(set(required_obligation_ids)))
    blockers: list[str] = []
    records_by_id: dict[str, tuple[CompilerObligationRecord, ObligationEvidenceVerdict]] = {}

    for record, evidence_verdict in evaluations:
        if record.obligation_id in records_by_id:
            blockers.append(f"duplicate obligation record: {record.obligation_id}")
            continue
        records_by_id[record.obligation_id] = (record, evidence_verdict)

    missing = sorted(set(required) - set(records_by_id))
    if not required:
        blockers.append("certification suite has no required obligation IDs")
    if missing:
        blockers.append(f"required obligation records are missing: {missing}")

    passed: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []
    unknown: list[str] = []

    for obligation_id in required:
        pair = records_by_id.get(obligation_id)
        if pair is None:
            unknown.append(obligation_id)
            continue
        record, verdict = pair
        if record.source_graph_hash != expected_source_graph_hash:
            blockers.append(f"{obligation_id}: source graph hash does not match certification target")
            unknown.append(obligation_id)
            continue

        if record.applicability is Applicability.NOT_APPLICABLE:
            if record.disposition is Disposition.NOT_APPLICABLE and verdict.disposition is Disposition.NOT_APPLICABLE:
                blockers.append(f"{obligation_id}: required suite obligation was marked NOT_APPLICABLE")
                blocked.append(obligation_id)
            else:
                blockers.append(f"{obligation_id}: invalid NOT_APPLICABLE disposition")
                unknown.append(obligation_id)
            continue

        if record.disposition is Disposition.FAIL or verdict.disposition is Disposition.FAIL:
            failed.append(obligation_id)
            blockers.append(f"{obligation_id}: failure is recorded")
        elif record.disposition in (
            Disposition.BLOCKED_NO_CONSUMER,
            Disposition.BLOCKED_UNRESOLVED,
            Disposition.UNSUPPORTED,
        ) or verdict.disposition in (
            Disposition.BLOCKED_NO_CONSUMER,
            Disposition.BLOCKED_UNRESOLVED,
            Disposition.UNSUPPORTED,
            Disposition.NOT_APPLICABLE,
        ):
            blocked.append(obligation_id)
            blockers.append(f"{obligation_id}: evidence is blocked or unsupported")
        elif verdict.disposition is Disposition.PASS and verdict.ok:
            passed.append(obligation_id)
        else:
            unknown.append(obligation_id)
            blockers.append(f"{obligation_id}: evidence has not independently passed")

    if failed:
        disposition = Disposition.FAIL
    elif blocked:
        disposition = Disposition.BLOCKED_UNRESOLVED
    elif blockers or unknown or len(passed) != len(required):
        disposition = Disposition.UNKNOWN
    else:
        disposition = Disposition.PASS

    return ObligationCertificationVerdict(
        disposition=disposition,
        required_obligations=required,
        passed_obligations=tuple(sorted(passed)),
        blocked_obligations=tuple(sorted(blocked)),
        failed_obligations=tuple(sorted(failed)),
        unknown_obligations=tuple(sorted(unknown)),
        blockers=tuple(blockers),
    )
