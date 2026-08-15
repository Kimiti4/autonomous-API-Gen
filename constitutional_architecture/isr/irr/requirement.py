"""
Requirement Types and Builders.

Provides structured requirement construction from natural language intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.isr.irr.model import (
    AcceptanceCriterion,
    IRR,
    Requirement,
    RequirementPriority,
    RequirementType,
)


class RequirementBuilder:
    """Fluent builder for constructing requirements."""

    def __init__(self) -> None:
        self._requirements: list[Requirement] = []
        self._nfrs: list[Requirement] = []
        self._domain_concepts: list[str] = []
        self._constraints: list[str] = []

    def add_functional(
        self,
        id: str,
        title: str,
        description: str = "",
        priority: RequirementPriority = RequirementPriority.MUST,
        acceptance_criteria: list[AcceptanceCriterion] | None = None,
        domain_concepts: list[str] | None = None,
    ) -> "RequirementBuilder":
        self._requirements.append(Requirement(
            id=id,
            title=title,
            requirement_type=RequirementType.FUNCTIONAL,
            description=description,
            priority=priority,
            acceptance_criteria=tuple(acceptance_criteria or []),
            domain_concepts=tuple(domain_concepts or []),
        ))
        if domain_concepts:
            self._domain_concepts.extend(domain_concepts)
        return self

    def add_non_functional(
        self,
        id: str,
        title: str,
        description: str = "",
        priority: RequirementPriority = RequirementPriority.MUST,
    ) -> "RequirementBuilder":
        self._nfrs.append(Requirement(
            id=id,
            title=title,
            requirement_type=RequirementType.NON_FUNCTIONAL,
            description=description,
            priority=priority,
        ))
        return self

    def add_constraint(self, constraint: str) -> "RequirementBuilder":
        self._constraints.append(constraint)
        return self

    def add_domain_concept(self, concept: str) -> "RequirementBuilder":
        self._domain_concepts.append(concept)
        return self

    def build(self, id: str, name: str, description: str = "") -> IRR:
        return IRR(
            id=id,
            name=name,
            description=description,
            requirements=tuple(self._requirements),
            domain_concepts=tuple(set(self._domain_concepts)),
            constraints=tuple(self._constraints),
            non_functional_requirements=tuple(self._nfrs),
        )
