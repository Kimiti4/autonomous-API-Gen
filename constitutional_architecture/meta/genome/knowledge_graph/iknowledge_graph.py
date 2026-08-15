"""
Phase 4: Design Knowledge Graph — Plugin Interface.

The DKG is the FEE's long-term semantic memory. It stores abstract
architectural patterns (not CSS or components) and maps them to
Genome Modifiers for seeding populations and guiding mutations.

Plugin-First Architecture: storage is abstracted behind an interface
for future migration to Neo4j, FalkorDB, or vector databases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Optional


@unique
class ChromosomeTarget(str, Enum):
    PRESENTATION = "Presentation"
    STRUCTURE = "Structure"
    BEHAVIOR = "Behavior"
    COMPOSITION = "Composition"


@unique
class ModifierOperation(str, Enum):
    SET = "set"
    MULTIPLY = "multiply"
    ADD = "add"
    CONSTRAIN = "constrain"


@unique
class PatternCategory(str, Enum):
    LAYOUT = "Layout"
    TYPOGRAPHY = "Typography"
    COLOR = "Color"
    INTERACTION = "Interaction"
    COMPOSITION = "Composition"


@dataclass(frozen=True)
class GenomeModifier:
    target_chromosome: ChromosomeTarget
    target_gene: str
    operation: ModifierOperation
    value: Any


@dataclass(frozen=True)
class DesignPattern:
    id: str
    name: str
    category: PatternCategory
    description: str
    applicability: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    genome_modifiers: tuple[GenomeModifier, ...] = ()


@dataclass(frozen=True)
class ContextTag:
    domain: str = ""
    user_intent: str = ""
    density_requirement: str = "comfortable"


class IKnowledgeGraph(ABC):
    @abstractmethod
    def resolve_patterns(self, context_tags: list[str]) -> list[DesignPattern]:
        ...

    @abstractmethod
    def get_pattern(self, pattern_id: str) -> Optional[DesignPattern]:
        ...

    @abstractmethod
    def register_pattern(self, pattern: DesignPattern) -> None:
        ...

    @abstractmethod
    def get_conflicting(self, pattern_id: str) -> list[DesignPattern]:
        ...
