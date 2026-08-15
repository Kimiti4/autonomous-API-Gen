"""
ASE-OS Learning Kernel: CKB Evolution.

Updates architectural patterns based on empirical survival-of-the-fittest.
Patterns are no longer static rules — they are probabilistic models backed
by evidence, with confidence scores updated Bayesian-style from experiment
outcomes recorded in the UEM.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from constitutional_architecture.core.kernels.engineering.uem import (
    EventType, UEMEvent, UniversalEngineeringMemory,
)


class EmpiricalEvidence(BaseModel):
    experiment_id: str
    context: str
    latency_ms: float
    error_rate: float
    outcome: str  # "survived" or "deprecated"


class ArchitecturalPattern(BaseModel):
    pattern_id: str
    name: str
    applicability: List[str] = Field(default_factory=list)
    trade_offs: List[str] = Field(default_factory=list)
    evidence: List[EmpiricalEvidence] = Field(default_factory=list)
    confidence_score: float = 0.5  # 0.0 to 1.0


class LearningKernel:
    def __init__(self, uem: UniversalEngineeringMemory) -> None:
        self.uem = uem
        self.ckb: Dict[str, ArchitecturalPattern] = {}

    def record_outcome(self, pattern_id: str,
                       evidence: EmpiricalEvidence) -> None:
        if pattern_id not in self.ckb:
            self.ckb[pattern_id] = ArchitecturalPattern(
                pattern_id=pattern_id, name=pattern_id)

        pattern = self.ckb[pattern_id]
        pattern.evidence.append(evidence)

        survivals = sum(
            1 for e in pattern.evidence if e.outcome == "survived")
        pattern.confidence_score = survivals / len(pattern.evidence)

        self.uem.append(UEMEvent(
            event_type=EventType.CKB_UPDATED,
            actor_id="LearningKernel",
            target_id=pattern_id,
            payload={
                "new_confidence": pattern.confidence_score,
                "evidence_id": evidence.experiment_id,
            },
        ))

    def get_pattern(self, pattern_id: str) -> ArchitecturalPattern:
        return self.ckb[pattern_id]

    @property
    def patterns(self) -> Dict[str, ArchitecturalPattern]:
        return dict(self.ckb)
