"""Technology-neutral capability semantics at the compiler boundary.

This module describes *what* a requested capability means to compilation.
It intentionally contains no framework, language, transport, or deployment
syntax. Concrete compiler backends translate these semantics into artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.engine.capability_contract import CapabilityResult, assess_genome
from app.engine.genome import Genome


@dataclass(frozen=True)
class CapabilityPlan:
    """Immutable semantic plan derived from an architecture/Genome."""

    requested: tuple[str, ...]
    implemented: tuple[str, ...]
    unmapped: tuple[str, ...]
    details: Mapping[str, CapabilityResult]

    def requires(self, name: str) -> bool:
        return name in self.requested

    def is_implemented(self, name: str) -> bool:
        return name in self.implemented


def plan_capabilities(genome: Genome) -> CapabilityPlan:
    """Derive backend-neutral capability semantics without generating code."""
    results = assess_genome(genome)
    requested = tuple(result.name for result in results if result.requested)
    implemented = tuple(result.name for result in results if result.requested and result.implemented)
    unmapped = tuple(result.name for result in results if result.requested and not result.implemented)
    return CapabilityPlan(
        requested=requested,
        implemented=implemented,
        unmapped=unmapped,
        details={result.name: result for result in results},
    )


def plan_from_architecture(architecture: Mapping[str, Any]) -> CapabilityPlan:
    """Build semantic capability intent from an architecture mapping."""
    return plan_capabilities(Genome(dict(architecture)))
