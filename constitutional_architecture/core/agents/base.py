"""
Phase 19 — Multi-Agent Primitives.

Defines the interface for specialized engineering agents and the artifacts
they produce. Agents interact strictly through the ISR/Intent vocabulary;
they never mention frameworks or cloud providers.

Constitutional Alignment:
- "Each agent should produce evidence-based recommendations": every Critique
  must carry a rationale and its Pareto impact.
- Axiom I (ISR Supremacy): agents emit directives over semantic nodes only.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from constitutional_architecture.core.models.intent import QualityAttribute


class ObjectionSeverity(str, Enum):
    INFO = "info"           # Suggestion for optimization
    WARNING = "warning"     # Trade-off identified, requires coordinator review
    FATAL = "fatal"         # Constitutional violation or critical blind spot.


class ArchitecturalDirective(BaseModel):
    """
    A hard constraint or weight adjustment injected by an agent into the
    Intent/Genome. Example: SecurityAgent dictates that
    'security_classification' MUST be 'restricted'.
    """

    target_node: str        # e.g., "CAPABILITY:patient_record" or "GLOBAL"
    attribute: str          # e.g., "security_classification"
    value: Any              # e.g., "restricted"
    rationale: str          # Evidence-based reasoning (CKB or Constitution)


class Critique(BaseModel):
    """An agent's objection to the current draft."""

    agent_role: str
    severity: ObjectionSeverity
    message: str
    proposed_directives: List[ArchitecturalDirective] = Field(
        default_factory=list)
    pareto_impact: Dict[QualityAttribute, float] = Field(default_factory=dict)


class Agent(BaseModel):
    """Base class for specialized engineering agents."""

    role: str

    def analyze(self, draft_intent: Dict[str, Any],
                context: Dict[str, Any]) -> List[Critique]:
        """Subclasses implement specific domain analysis."""
        raise NotImplementedError
