"""
Frontend ISR Profile — Python domain model.

Defines frontend architecture entities as technology-neutral dataclasses
that extend the platform ISR. These are the FISR entities referenced
by the Frontend Evolution Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Optional


@unique
class ChromosomeFamily(str, Enum):
    """Chromosome families that map frontend entities to the Evolution Engine."""
    PRESENTATION = "Presentation"
    STRUCTURE = "Structure"
    BEHAVIOR = "Behavior"
    COMPLIANCE = "Compliance"
    STATE = "State"


@dataclass(frozen=True)
class GenomeMapping:
    """Links a frontend entity to the Evolution Engine's genome."""
    chromosome_family: ChromosomeFamily
    gene_id: str
    mutation_rate: float = 0.1


@dataclass(frozen=True)
class FitnessTarget:
    """Declares which automated evaluator must assess this entity."""
    evaluator_plugin: str
    threshold: float = 0.75
    weight: float = 0.1


@dataclass(frozen=True)
class AccessibilityContract:
    """WCAG and ARIA requirements for a component or page."""
    aria_role: str = ""
    keyboard_navigation: tuple[str, ...] = ()
    screen_reader_annotations: dict[str, str] = field(default_factory=dict)
    focus_management: str = "sequential"
    wcag_target: str = "AA"


@dataclass(frozen=True)
class PropertyDefinition:
    """Typed input property for a component."""
    name: str
    type: str = "string"
    required: bool = False
    default_value: Any = None


@dataclass(frozen=True)
class EventDefinition:
    """Output event emitted by a component."""
    name: str
    payload_type: str = "any"
    description: str = ""


@dataclass(frozen=True)
class ComponentNode:
    """An instance of a component within a page or layout tree."""
    component_ref: str
    props: dict[str, Any] = field(default_factory=dict)
    children: tuple[ComponentNode, ...] = ()


@dataclass(frozen=True)
class TokenDefinition:
    """Atomic semantic design token. NEVER raw CSS/Hex — resolved via compiler backend."""
    id: str
    semantic_role: str
    category: str
    base_value: Any
    description: str = ""
    variants: dict[str, Any] = field(default_factory=dict)
    accessibility_constraints: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class DesignSystem:
    """Root container for semantic design tokens and brand identity."""
    id: str
    name: str
    tokens: dict[str, dict[str, TokenDefinition]] = field(default_factory=dict)
    genome: Optional[GenomeMapping] = None


@dataclass(frozen=True)
class GridSystem:
    """Grid definition within a layout."""
    columns: int = 12
    gutter_token_ref: str = ""
    margin_token_ref: str = ""


@dataclass(frozen=True)
class Component:
    """Reusable UI building block — defines API, states, composition rules."""
    id: str
    name: str
    purpose: str
    inputs: tuple[PropertyDefinition, ...] = ()
    outputs: tuple[EventDefinition, ...] = ()
    states: tuple[str, ...] = ("default",)
    variants: tuple[str, ...] = ()
    allowed_children: tuple[str, ...] = ()
    allowed_parents: tuple[str, ...] = ()
    token_dependencies: tuple[str, ...] = ()
    accessibility_contract: AccessibilityContract = field(default_factory=AccessibilityContract)
    genome: Optional[GenomeMapping] = None
    fitness_targets: tuple[FitnessTarget, ...] = ()


@dataclass(frozen=True)
class Layout:
    """Structural composition rules — grids, shells, regions."""
    id: str
    name: str
    grid_system: Optional[GridSystem] = None
    responsive_breakpoints: tuple[str, ...] = ()
    regions: tuple[dict[str, str], ...] = ()
    genome: Optional[GenomeMapping] = None


@dataclass(frozen=True)
class Interaction:
    """Behavioral definition — motion, gestures, transitions."""
    id: str
    name: str
    trigger: str
    motion_token_ref: str = ""
    state_transition: Optional[dict[str, str]] = None
    reduced_motion_fallback: bool = False


@dataclass(frozen=True)
class Page:
    """Route-level orchestration — links frontend ISR to backend ISR data contracts."""
    id: str
    name: str
    route_pattern: str
    layout_ref: str
    component_tree: ComponentNode = field(default_factory=lambda: ComponentNode(component_ref="root"))
    data_requirements: tuple[str, ...] = ()
    view_states: dict[str, ComponentNode] = field(default_factory=dict)
    genome: Optional[GenomeMapping] = None
    fitness_targets: tuple[FitnessTarget, ...] = ()


@dataclass(frozen=True)
class FrontendISRProfile:
    """
    Top-level container for the Frontend ISR Profile.

    This is embedded within the platform ISR as a profile extension.
    It does not replace the ISR — it extends it.
    """
    design_system: DesignSystem
    components: tuple[Component, ...] = ()
    layouts: tuple[Layout, ...] = ()
    pages: tuple[Page, ...] = ()
    interactions: tuple[Interaction, ...] = ()
