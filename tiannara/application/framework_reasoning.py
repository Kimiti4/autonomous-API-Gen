"""Framework selection reasoning primitives.

These functions rank framework candidates from explicit ISR needs plus
provenance-backed knowledge. They do not contain framework-specific generation
rules. Missing knowledge remains uncertainty instead of becoming a positive
assumption.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .framework_knowledge import FrameworkKnowledgePack

@dataclass(frozen=True)
class FrameworkNeed:
    capability: str
    importance: float
    rationale: str

@dataclass(frozen=True)
class FrameworkAssessment:
    framework_id: str
    score: float
    matched_needs: tuple[str, ...]
    unknown_needs: tuple[str, ...]
    constraints: tuple[str, ...]
    rationale: str

def assess_framework(pack: FrameworkKnowledgePack, needs: Iterable[FrameworkNeed]) -> FrameworkAssessment:
    matched=[]; unknown=[]; score=0.0; total=0.0
    for need in needs:
        weight=max(0.0, need.importance)
        total += weight
        value=pack.capability(need.capability)
        if value is None:
            unknown.append(need.capability)
            continue
        if value.lower() in {"strong","supported","excellent"}:
            score += weight
            matched.append(need.capability)
        elif value.lower() in {"partial","limited"}:
            score += weight * 0.5
            matched.append(need.capability)
    normalized=score/total if total else 0.0
    return FrameworkAssessment(
        framework_id=pack.framework_id,
        score=normalized,
        matched_needs=tuple(matched),
        unknown_needs=tuple(unknown),
        constraints=pack.constraints,
        rationale=f"Score is evidence-bounded: {len(matched)} needs matched, {len(unknown)} remain unknown."
    )

def rank_frameworks(packs: Iterable[FrameworkKnowledgePack], needs: Iterable[FrameworkNeed]) -> tuple[FrameworkAssessment, ...]:
    need_tuple=tuple(needs)
    return tuple(sorted((assess_framework(p,need_tuple) for p in packs),
                        key=lambda x: (x.score, -len(x.unknown_needs)), reverse=True))
