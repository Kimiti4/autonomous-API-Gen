"""Canonical, immutable evidence record for one ESAP evolution transaction."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .candidate_measurements import CandidateMeasurementResult
from .dependency_reexecution import DependencyExecutionResult
from .evidence_scoring import DerivedArchitectureScore
from .repair_coevolution import RepairExecution
from .rejection_analysis import RejectionRecord
from .successor_admission import SuccessorAdmission, SuccessorEvent


@dataclass(frozen=True)
class TransactionEvidenceRecord:
    """Machine-readable, content-addressed record of a governed transaction."""

    schema_version: str
    transaction_id: str
    source_event_id: str
    source_architecture_id: str
    successor_event_id: str
    successor_architecture_id: str
    mutations: tuple[Mapping[str, Any], ...]
    repair_reports: tuple[Mapping[str, Any], ...]
    dependency_reports: tuple[Mapping[str, Any], ...]
    measurements: tuple[Mapping[str, Any], ...]
    score: Mapping[str, Any]
    admission: Mapping[str, Any]
    rejection: Mapping[str, Any] | None
    residuals: tuple[str, ...]
    evidence: tuple[str, ...]
    parent_digest: str | None
    digest: str

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "transaction_id": self.transaction_id,
            "source_event_id": self.source_event_id,
            "source_architecture_id": self.source_architecture_id,
            "successor_event_id": self.successor_event_id,
            "successor_architecture_id": self.successor_architecture_id,
            "mutations": list(self.mutations),
            "repair_reports": list(self.repair_reports),
            "dependency_reports": list(self.dependency_reports),
            "measurements": list(self.measurements),
            "score": dict(self.score),
            "admission": dict(self.admission),
            "rejection": dict(self.rejection) if self.rejection is not None else None,
            "residuals": list(self.residuals),
            "evidence": list(self.evidence),
            "parent_digest": self.parent_digest,
        }

    def verify_digest(self) -> bool:
        return self.digest == _digest(self.canonical_payload())

    def to_json(self) -> str:
        return json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))


def materialize_transaction_evidence(
    *,
    transaction_id: str,
    source_event_id: str,
    source_architecture_id: str,
    successor: SuccessorEvent,
    repairs: Sequence[RepairExecution],
    dependency: DependencyExecutionResult,
    measurements: CandidateMeasurementResult,
    score: DerivedArchitectureScore,
    admission: SuccessorAdmission | None,
    parent_digest: str | None = None,
    rejection: RejectionRecord | None = None,
    counterfactuals: Sequence[Mapping[str, Any]] = (),
) -> TransactionEvidenceRecord:
    mutation_rows = tuple(
        {"domain": c.domain, "mutation_id": c.mutation_id, "properties": list(c.properties)}
        for c in successor.event.changes
    )
    repair_rows = tuple(
        {
            "domain": r.candidate.domain,
            "mutation_id": r.candidate.repair_mutation_id,
            "passed": r.verification.passed,
            "evidence": [e for gate in r.verification.results for e in gate.evidence],
        }
        for r in repairs
    )
    dependency_rows = tuple(
        {
            "domain": x.domain,
            "mutation_id": x.mutation_id,
            "passed": x.verification.passed,
            "evidence": [e for gate in x.verification.results for e in gate.evidence],
        }
        for x in dependency.executions
    )
    measurement_rows = tuple(
        {"objective": m.objective, "value": m.value, "evidence": list(m.evidence)}
        for m in measurements.measurements
    )
    residuals = tuple(sorted(dependency.closure.residuals))
    evidence = tuple(sorted(set(successor.evidence) | set(score.score.evidence)))
    admission_row = {
        "admitted": (
            admission is not None
            and successor.passed
            and admission.member.lineage.architecture_id == successor.architecture_id
        ),
        "architecture_id": admission.member.lineage.architecture_id if admission else None,
        "generation": admission.member.lineage.generation if admission else None,
    }
    rejection_row = None
    if rejection is not None:
        rejection_row = {
            "status": rejection.status,
            "reasons": list(rejection.reasons),
            "frontier": list(rejection.frontier),
            "counterfactuals": [dict(x) for x in counterfactuals],
        }
    payload = {
        "schema_version": "esap.transaction-evidence.v2",
        "transaction_id": transaction_id,
        "source_event_id": source_event_id,
        "source_architecture_id": source_architecture_id,
        "successor_event_id": successor.event.event_id,
        "successor_architecture_id": successor.architecture_id,
        "mutations": list(mutation_rows),
        "repair_reports": list(repair_rows),
        "dependency_reports": list(dependency_rows),
        "measurements": list(measurement_rows),
        "score": {
            "architecture_id": score.score.architecture_id,
            "values": dict(score.score.values),
            "evidence": list(score.score.evidence),
        },
        "admission": admission_row,
        "rejection": rejection_row,
        "residuals": list(residuals),
        "evidence": list(evidence),
        "parent_digest": parent_digest,
    }
    return TransactionEvidenceRecord(**payload, digest=_digest(payload))


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
