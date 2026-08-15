"""
IRR — Intermediate Requirement Representation

The IRR captures intent independently from architecture. Requirements
and architecture evolve independently. Separating IRR from ISR allows
requirements to remain stable while architecture evolves freely.

The IRR captures:
- User Stories — expressed intent
- Functional Requirements — what the system must do
- Non-Functional Requirements — quality attributes
- Constraints — hard boundaries
- Domain Concepts — entities, relationships, processes
- Acceptance Criteria — measurable conditions for satisfaction
"""

from constitutional_architecture.irr.schema import (
    IRR, UserStory, FunctionalRequirement, NonFunctionalRequirement,
    Constraint as IRRConstraint, DomainConcept, AcceptanceCriterion,
    RequirementGraph, RequirementNode, RequirementEdge,
    RequirementRelationType, build_requirement_graph,
    capture_ecommerce_requirements
)

__all__ = [
    "IRR", "UserStory", "FunctionalRequirement", "NonFunctionalRequirement",
    "IRRConstraint", "DomainConcept", "AcceptanceCriterion",
    "RequirementGraph", "RequirementNode", "RequirementEdge",
    "RequirementRelationType", "build_requirement_graph",
    "capture_ecommerce_requirements",
]