"""
IRR Model.

The Intermediate Requirement Representation captures user intent
in a structured, technology-neutral form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Optional


@unique
class RequirementType(str, Enum):
    """Types of requirements."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    DOMAIN_CONCEPT = "domain_concept"
    USER_STORY = "user_story"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"

    def __str__(self) -> str:
        return self.value


@unique
class RequirementPriority(str, Enum):
    """Priority level of a requirement."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AcceptanceCriterion:
    """A measurable condition for requirement satisfaction."""

    id: str
    description: str
    measurable: bool = True
    metric: str = ""
    threshold: str = ""


@dataclass(frozen=True)
class Requirement:
    """
    A single structured requirement.

    Technology-neutral. Captures WHAT is needed, not HOW.
    """

    id: str
    title: str
    requirement_type: RequirementType
    description: str = ""
    priority: RequirementPriority = RequirementPriority.MUST
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    related_requirements: tuple[str, ...] = ()
    domain_concepts: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IRR:
    """
    The Intermediate Requirement Representation.

    Captures all requirements in a structured, technology-neutral form.
    The IRR is STABLE: it changes only when requirements change,
    not when architecture evolves.
    """

    id: str
    name: str
    description: str = ""
    requirements: tuple[Requirement, ...] = ()
    domain_concepts: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    non_functional_requirements: tuple[Requirement, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_requirement(self, req_id: str) -> Optional[Requirement]:
        for r in self.requirements:
            if r.id == req_id:
                return r
        return None

    @property
    def functional_requirements(self) -> tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if r.requirement_type == RequirementType.FUNCTIONAL)

    @property
    def must_have_requirements(self) -> tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if r.priority == RequirementPriority.MUST)
