"""
ISR System Model — root container for the complete software system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.model.deployment import Deployment
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.semantics.boundary import ArchitecturalBoundary
from constitutional_architecture.isr.semantics.capability import BusinessCapability
from constitutional_architecture.isr.semantics.decision import ArchitecturalDecision
from constitutional_architecture.isr.semantics.deployment import DeploymentIntent
from constitutional_architecture.isr.semantics.reliability import ReliabilityRequirement
from constitutional_architecture.isr.semantics.requirement import (
    AcceptanceCriterion,
    Requirement,
)
from constitutional_architecture.isr.semantics.testing_anchor import TestingAnchor


@dataclass(frozen=True)
class SystemMetadata:
    version: str = "1.0"
    authors: tuple[str, ...] = ()
    license: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class System:
    id: str
    name: str
    description: str = ""
    modules: tuple[Module, ...] = ()
    # Environment attributes: WHERE the system runs (tier, scaling bounds,
    # networking, monitoring paths, storage, secrets). Distinct from
    # deployment_intents (R2.10.3-G), which declares the LIFECYCLE contract:
    # WHAT a change must accomplish, under what conditions, WHAT must remain
    # preserved, WHEN rollback is required. Environment vs intent — never
    # mixed, both empty identity-neutral (Option A).
    deployment: Optional[Deployment] = None
    metadata: SystemMetadata = field(default_factory=SystemMetadata)
    global_policies: tuple[str, ...] = ()
    constraints: tuple = ()
    business_capabilities: tuple[BusinessCapability, ...] = ()
    reliability_requirements: tuple[ReliabilityRequirement, ...] = ()
    architectural_boundaries: tuple[ArchitecturalBoundary, ...] = ()
    requirements: tuple[Requirement, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    deployment_intents: tuple[DeploymentIntent, ...] = ()
    testing_anchors: tuple[TestingAnchor, ...] = ()
    # Documentation intents (R2.10.3-I): WHAT must be documented, for whom,
    # and why — semantic, never a format or path. One-way direction:
    # ISR semantics -> intent -> realization. Documentation references its
    # subjects by identity and cannot author them (non-authority is
    # structural, so it can never become a second source of truth).
    documentation_intents: tuple[DocumentationIntent, ...] = ()
    # Evolution policy (R2.10.3-J): WHAT evolution is allowed to optimize
    # (objectives) and WHAT it is constitutionally forbidden to sacrifice
    # (protected regions), composed by policies. All three are separate
    # semantic genes; all empty identity-neutral (Option A). J is the
    # constitutional declaration of evolution authority — never engine
    # configuration, never measurements.
    evolution_objectives: tuple[EvolutionObjective, ...] = ()
    protected_regions: tuple[ProtectedRegion, ...] = ()
    evolution_policies: tuple[EvolutionPolicy, ...] = ()
    # Architectural decisions (R2.10.32.1): the decision record — WHY the
    # system's shape is what it is, in ADR-complete form (context, question,
    # alternatives, selection, justification, rejected alternatives, future
    # evolution). The ISR is the only author of decisions: Phase 32
    # (certification) is their CONSUMER, never their author. Reference
    # edges resolve against existing constructs (requirements from F,
    # invariants from E/D/J, modules, anchors from H) — the carrier authors
    # no new obligation. Empty identity-neutral (Option A).
    architectural_decisions: tuple[ArchitecturalDecision, ...] = ()

    def get_module(self, module_id: str) -> Optional[Module]:
        for m in self.modules:
            if m.id == module_id:
                return m
        return None

    @property
    def all_module_ids(self) -> frozenset[str]:
        return frozenset(m.id for m in self.modules)

    @property
    def module_count(self) -> int:
        return len(self.modules)
