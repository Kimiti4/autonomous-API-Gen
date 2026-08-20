"""
ISR — The Top-Level Immutable Container.

The ISR is the constitutional source of truth. It is immutable.
Every mutation produces a new ISR version. No mutation may modify
an existing ISR in place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.boundary import (
    validate_system_boundary_constraints,
)
from constitutional_architecture.isr.semantics.capability import (
    validate_system_capability_constraints,
)
from constitutional_architecture.isr.semantics.deployment import (
    validate_system_deployment_constraints,
)
from constitutional_architecture.isr.semantics.documentation import (
    validate_system_documentation_constraints,
)
from constitutional_architecture.isr.semantics.decision import (
    validate_system_decision_constraints,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    validate_system_evolution_policy_constraints,
)
from constitutional_architecture.isr.semantics.migration import (
    validate_module_migration_constraints,
)
from constitutional_architecture.isr.semantics.projection import semantic_content_hash
from constitutional_architecture.isr.semantics.reliability import (
    validate_system_reliability_constraints,
)
from constitutional_architecture.isr.semantics.requirement import (
    validate_system_requirement_constraints,
)
from constitutional_architecture.isr.semantics.testing_anchor import (
    validate_system_testing_anchor_constraints,
)
from constitutional_architecture.isr.semantics.threat import (
    validate_system_threat_constraints,
)
from constitutional_architecture.isr.semantics.temporal import (
    validate_module_temporal_constraints,
)


@dataclass(frozen=True)
class ISRProvenance:
    """Provenance information for an ISR version."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    parent_hash: Optional[str] = None
    mutation_description: str = ""
    evolution_run_id: Optional[str] = None
    generation: int = 0


@dataclass(frozen=True)
class ISR:
    """
    The Intermediate Software Representation.

    This is the constitutional source of truth for all software architecture.
    It is IMMUTABLE. Every mutation produces a new ISR instance.

    The ISR answers: "What should exist?"
    It never answers: "How does [framework] implement it?"
    """

    system: System
    version: int = 1
    provenance: ISRProvenance = field(default_factory=ISRProvenance)
    _content_hash: Optional[str] = field(default=None, repr=False)

    @property
    def content_hash(self) -> str:
        """Semantic content hash (Phase-28 identity migration).

        Projects only the architectural payload (``system``), excluding
        version, provenance, and the hash cache — stable across runs while
        preserving governance change-detection over the full System/Module
        tree. Does NOT route through ISRSerializer (avoids its default=str
        anti-pattern).
        """
        if self._content_hash is not None:
            return self._content_hash
        return semantic_content_hash(self)

    @property
    def id(self) -> str:
        return f"isr-{self.system.id}-v{self.version}-{self.content_hash[:12]}"

    def with_system(self, new_system: System) -> "ISR":
        return ISR(
            system=new_system,
            version=self.version + 1,
            provenance=ISRProvenance(
                parent_hash=self.content_hash,
                generation=self.provenance.generation + 1,
            ),
        )

    def validate_structure(self) -> bool:
        if not self.system.modules:
            return False
        module_ids = set()
        for module in self.system.modules:
            if module.id in module_ids:
                return False
            module_ids.add(module.id)
            if validate_module_temporal_constraints(module):
                return False
            if validate_module_migration_constraints(module):
                return False
        if validate_system_capability_constraints(self.system):
            return False
        if validate_system_reliability_constraints(self.system):
            return False
        if validate_system_boundary_constraints(self.system):
            return False
        if validate_system_requirement_constraints(self.system):
            return False
        if validate_system_deployment_constraints(self.system):
            return False
        if validate_system_documentation_constraints(self.system):
            return False
        if validate_system_evolution_policy_constraints(self.system):
            return False
        if validate_system_decision_constraints(self.system):
            return False
        if validate_system_threat_constraints(self.system):
            return False
        if validate_system_testing_anchor_constraints(self.system):
            return False
        return True
