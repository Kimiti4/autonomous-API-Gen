"""
ISR System Model — root container for the complete software system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.model.deployment import Deployment
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.semantics.capability import BusinessCapability
from constitutional_architecture.isr.semantics.reliability import ReliabilityRequirement


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
    deployment: Optional[Deployment] = None
    metadata: SystemMetadata = field(default_factory=SystemMetadata)
    global_policies: tuple[str, ...] = ()
    constraints: tuple = ()
    business_capabilities: tuple[BusinessCapability, ...] = ()
    reliability_requirements: tuple[ReliabilityRequirement, ...] = ()

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
