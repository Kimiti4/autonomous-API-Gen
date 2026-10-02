"""Selection gate that preserves engineering freedom while requiring quality evidence."""
from __future__ import annotations
from dataclasses import dataclass
from .architecture_quality import CandidateQualityEvaluation
from .engineering_deliberation import EngineeringDeliberation


@dataclass(frozen=True)
class SelectionReadiness:
    ready: bool
    findings: tuple[str, ...]


def selection_readiness(
    deliberation: EngineeringDeliberation,
    evaluations: tuple[CandidateQualityEvaluation, ...],
) -> SelectionReadiness:
    findings: list[str] = []
    ids = {e.alternative_id for e in evaluations}
    if deliberation.selected_alternative and deliberation.selected_alternative not in ids:
        findings.append("selected architecture has no quality evaluation")
    for e in evaluations:
        if e.missing:
            findings.append(
                f"{e.alternative_id} has unverified quality obligations: {','.join(e.missing)}"
            )
    if deliberation.unresolved:
        findings.append("selection has unresolved engineering questions")
    return SelectionReadiness(not findings, tuple(findings))
