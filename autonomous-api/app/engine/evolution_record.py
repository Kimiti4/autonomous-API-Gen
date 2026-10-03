"""Traceable architecture evolution records.

Records preserve why an architectural change occurred without granting
the record itself authority to mutate the ISR.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionRecord:
    evolution_id: str
    parent_architecture_id: str
    candidate_id: str
    trigger_counterexample_id: str | None
    supporting_evidence_ids: tuple[str, ...]
    unresolved_risks: tuple[str, ...]
    changed_assumptions: tuple[str, ...]
    preserved_invariants: tuple[str, ...]
    authority_reference: str
    status: str = "proposed"


@dataclass(frozen=True)
class EvolutionLineage:
    records: tuple[EvolutionRecord, ...]


def validate_evolution(record: EvolutionRecord) -> tuple[str, ...]:
    errors = []
    if not record.evolution_id:
        errors.append("missing-evolution-id")
    if not record.parent_architecture_id:
        errors.append("missing-parent-architecture")
    if not record.candidate_id:
        errors.append("missing-candidate")
    if not record.authority_reference:
        errors.append("missing-authority-reference")
    if record.status not in {"proposed", "authorized", "implemented", "verified", "rejected"}:
        errors.append("invalid-status")
    if record.status in {"authorized", "implemented", "verified"} and not record.supporting_evidence_ids:
        errors.append("authorized-evolution-requires-evidence")
    return tuple(errors)


def append_evolution(
    lineage: EvolutionLineage,
    record: EvolutionRecord,
) -> EvolutionLineage:
    errors = validate_evolution(record)
    if errors:
        raise ValueError(";".join(errors))
    if any(r.evolution_id == record.evolution_id for r in lineage.records):
        raise ValueError("duplicate-evolution-id")
    return EvolutionLineage(lineage.records + (record,))


def lineage_for_architecture(
    lineage: EvolutionLineage,
    architecture_id: str,
) -> tuple[EvolutionRecord, ...]:
    return tuple(
        r for r in lineage.records
        if r.parent_architecture_id == architecture_id
    )
