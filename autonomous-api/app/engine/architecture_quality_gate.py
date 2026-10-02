"""Canonical quality-gate orchestration for architecture candidates."""
from __future__ import annotations
from dataclasses import dataclass
from .architecture_quality import CandidateQualityEvaluation, evaluate_candidates
from .engineering_deliberation import EngineeringDeliberation
from .engineering_capability import capability_for
from .quality_profiles import profile_for
from .selection_quality import SelectionReadiness, selection_readiness

@dataclass(frozen=True)
class ArchitectureQualityGate:
    role: str
    evaluations: tuple[CandidateQualityEvaluation, ...]
    selection: SelectionReadiness

def evaluate_architecture_quality(
    role: str,
    deliberation: EngineeringDeliberation,
) -> ArchitectureQualityGate:
    if role not in {"frontend", "backend", "fullstack"}:
        raise ValueError(f"unsupported engineering role: {role}")
    capability = capability_for(role)  # establishes the canonical obligations
    profile = profile_for(capability.role)
    evaluations = evaluate_candidates(deliberation.alternatives, profile)
    return ArchitectureQualityGate(
        role=role,
        evaluations=evaluations,
        selection=selection_readiness(deliberation, evaluations),
    )
