"""
EIR Model.

The Evolution Intermediate Representation captures architectural
transformations as first-class objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass


@dataclass(frozen=True)
class Transformation:
    """
    A single architectural transformation.

    Describes WHAT changed and WHY, not HOW it was implemented.
    """

    id: str
    transformation_type: str
    category: MutationCategory
    mutation_class: MutationClass
    target_node_id: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    fitness_impact: dict[str, float] = field(default_factory=dict)
    reversible: bool = True
    inverse_transformation: Optional[str] = None
    rationale: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class EIR:
    """
    The Evolution Intermediate Representation.

    An ordered sequence of architectural transformations that,
    when applied to a source ISR, produce a target ISR.

    EIRs enable:
    - Reversible transformations
    - Mutation replay
    - Learning which transformations improve fitness
    - Semantic architectural diffs
    - Explainable evolution
    """

    id: str
    source_isr_hash: str
    target_isr_hash: str = ""
    transformations: tuple[Transformation, ...] = ()
    proposed_by: str = ""
    generation: int = 0
    fitness_delta: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def transformation_count(self) -> int:
        return len(self.transformations)

    @property
    def is_reversible(self) -> bool:
        return all(t.reversible for t in self.transformations)

    @property
    def summary(self) -> str:
        if not self.transformations:
            return "Empty transformation set"
        return "; ".join(t.description for t in self.transformations if t.description)
