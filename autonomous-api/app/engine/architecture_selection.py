"""CAP-002 governed architecture candidate evaluation and selection.

Generation and selection are deliberately separate. This module can establish
admissibility from explicit obligation mappings, but it never silently chooses
an architecture on behalf of governance.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .architecture_ir import ArchitectureCandidate
from .architecture_obligations import (
    ArchitectureObligation, ObligationMapping, certify_architecture_mappings,
)


@dataclass(frozen=True)
class ArchitectureCandidateEvaluation:
    architecture_id: str
    admissible: bool
    findings: tuple[str, ...]
    mapped_obligations: int
    satisfied_obligations: int
    evidence_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture_id": self.architecture_id,
            "admissible": self.admissible,
            "findings": list(self.findings),
            "mapped_obligations": self.mapped_obligations,
            "satisfied_obligations": self.satisfied_obligations,
            "evidence_requirements": list(self.evidence_requirements),
        }


def evaluate_candidate(
    candidate: ArchitectureCandidate,
    obligations: tuple[ArchitectureObligation, ...],
    mappings: tuple[ObligationMapping, ...],
) -> ArchitectureCandidateEvaluation:
    findings = list(certify_architecture_mappings(obligations, mappings))
    expected = {o.obligation_id for o in obligations}
    valid = [m for m in mappings if m.obligation_id in expected]
    evidence = tuple(sorted({
        requirement
        for mapping in valid
        for requirement in mapping.evidence_requirements
    }))
    return ArchitectureCandidateEvaluation(
        candidate.architecture_id,
        not findings,
        tuple(findings),
        len(valid),
        sum(1 for m in valid if m.satisfied),
        evidence,
    )


@dataclass(frozen=True)
class ArchitectureSelectionRequest:
    request_id: str
    candidate_ids: tuple[str, ...]
    authorized_by: str | None = None
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | {"candidate_ids": list(self.candidate_ids)}


@dataclass(frozen=True)
class ArchitectureSelection:
    request_id: str
    selected_candidate_id: str
    authorized_by: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


def authorize_selection(
    request: ArchitectureSelectionRequest,
    evaluations: tuple[ArchitectureCandidateEvaluation, ...],
    *,
    selected_candidate_id: str,
    authorized_by: str,
    rationale: str,
) -> ArchitectureSelection:
    """Create an explicit selection record; no implicit ranking is performed."""
    if selected_candidate_id not in request.candidate_ids:
        raise ValueError("selected candidate is not part of selection request")
    evaluation = next(
        (e for e in evaluations if e.architecture_id == selected_candidate_id), None
    )
    if evaluation is None:
        raise ValueError("selected candidate has no evaluation")
    if not evaluation.admissible:
        raise ValueError("cannot authorize an inadmissible architecture")
    if not authorized_by.strip():
        raise ValueError("selection requires an explicit authority")
    if not rationale.strip():
        raise ValueError("selection requires an explicit rationale")
    return ArchitectureSelection(
        request.request_id, selected_candidate_id, authorized_by.strip(), rationale.strip()
    )
