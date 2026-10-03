"""Reconstruct the causal evolution history of an ESAP architecture."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence_ledger import EvidenceLedger
from .transaction_evidence import TransactionEvidenceRecord


@dataclass(frozen=True)
class EvolutionDecision:
    transaction_id: str
    source_architecture_id: str
    successor_architecture_id: str
    admitted: bool
    generation: int | None
    mutations: tuple[dict[str, Any], ...]
    repairs: tuple[dict[str, Any], ...]
    dependency_effects: tuple[dict[str, Any], ...]
    measurements: tuple[dict[str, Any], ...]
    score: dict[str, Any]
    residuals: tuple[str, ...]
    evidence: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class ArchitectureHistory:
    architecture_id: str
    decisions: tuple[EvolutionDecision, ...]
    chain_valid: bool
    root_architecture_id: str | None
    final_digest: str | None


def _decision(record: TransactionEvidenceRecord) -> EvolutionDecision:
    admission = dict(record.admission)
    return EvolutionDecision(
        transaction_id=record.transaction_id,
        source_architecture_id=record.source_architecture_id,
        successor_architecture_id=record.successor_architecture_id,
        admitted=bool(admission.get("admitted", False)),
        generation=admission.get("generation"),
        mutations=tuple(dict(x) for x in record.mutations),
        repairs=tuple(dict(x) for x in record.repair_reports),
        dependency_effects=tuple(dict(x) for x in record.dependency_reports),
        measurements=tuple(dict(x) for x in record.measurements),
        score=dict(record.score),
        residuals=record.residuals,
        evidence=record.evidence,
        digest=record.digest,
    )


def reconstruct_architecture_history(
    ledger: EvidenceLedger,
    architecture_id: str,
) -> ArchitectureHistory:
    """Return the complete causal chain ending at an architecture.

    The target may be either a source architecture or a successor. Every
    traversed record must be digest-valid and lineage-consistent.
    """
    if not ledger.verify():
        raise ValueError("history-invalid-ledger")
    if not architecture_id:
        raise ValueError("history-requires-architecture-id")

    decisions = []
    current = architecture_id
    while True:
        matching = [
            record for record in ledger.records
            if record.successor_architecture_id == current
        ]
        if not matching:
            break
        if len(matching) != 1:
            raise ValueError("history-ambiguous-successor:" + current)

        record = matching[0]
        decisions.append(_decision(record))
        current = record.source_architecture_id

    decisions.reverse()
    return ArchitectureHistory(
        architecture_id=architecture_id,
        decisions=tuple(decisions),
        chain_valid=ledger.verify(),
        root_architecture_id=current if decisions else None,
        final_digest=decisions[-1].digest if decisions else None,
    )


def explain_architecture_decision(
    ledger: EvidenceLedger,
    architecture_id: str,
) -> dict[str, Any]:
    """Produce a deterministic machine-readable causal explanation."""
    history = reconstruct_architecture_history(ledger, architecture_id)
    if not history.decisions:
        return {
            "architecture_id": architecture_id,
            "status": "no-evolution-record",
            "chain_valid": history.chain_valid,
        }

    final = history.decisions[-1]
    return {
        "architecture_id": architecture_id,
        "status": "admitted" if final.admitted else "not-admitted",
        "chain_valid": history.chain_valid,
        "root_architecture_id": history.root_architecture_id,
        "transaction_count": len(history.decisions),
        "final_transaction_id": final.transaction_id,
        "source_architecture_id": final.source_architecture_id,
        "mutations": final.mutations,
        "repairs": final.repairs,
        "dependency_effects": final.dependency_effects,
        "measurements": final.measurements,
        "score": final.score,
        "residuals": final.residuals,
        "evidence": final.evidence,
        "decision_digest": final.digest,
    }
