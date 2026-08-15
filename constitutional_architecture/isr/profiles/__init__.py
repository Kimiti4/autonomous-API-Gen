"""
ISR Profiles — domain-specific extensions of the core ISR schema.

Each profile adds entity types, edge types, and validation rules
that are meaningful for a specific architectural concern (frontend,
infrastructure, data, etc.) without modifying the core ISR.
"""

from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile,
    DesignSystem,
    TokenDefinition,
    Component,
    ComponentNode,
    Layout,
    GridSystem,
    Page,
    Interaction,
    AccessibilityContract,
    PropertyDefinition,
    EventDefinition,
    GenomeMapping,
    FitnessTarget,
    ChromosomeFamily,
)
from constitutional_architecture.isr.profiles.frontend_validator import FrontendProfileValidator
from constitutional_architecture.isr.profiles.frontend_transformer import FrontendTransformer

__all__ = [
    "FrontendISRProfile",
    "DesignSystem",
    "TokenDefinition",
    "Component",
    "ComponentNode",
    "Layout",
    "GridSystem",
    "Page",
    "Interaction",
    "AccessibilityContract",
    "PropertyDefinition",
    "EventDefinition",
    "GenomeMapping",
    "FitnessTarget",
    "ChromosomeFamily",
    "FrontendProfileValidator",
    "FrontendTransformer",
]
