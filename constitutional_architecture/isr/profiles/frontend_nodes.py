"""
Frontend ISR Node Types.

Extends the platform ISR NodeType enum with frontend-specific node types.
These exist as a separate namespace to preserve the core ISR's purity.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class FrontendNodeType(str, Enum):
    """Frontend-specific node types extending the platform ISR."""

    DESIGN_SYSTEM = "frontend.design_system"
    TOKEN = "frontend.token"
    COMPONENT = "frontend.component"
    COMPONENT_VARIANT = "frontend.component_variant"
    LAYOUT = "frontend.layout"
    PAGE = "frontend.page"
    INTERACTION = "frontend.interaction"
    ACCESSIBILITY_CONTRACT = "frontend.accessibility_contract"
    GRID = "frontend.grid"

    def __str__(self) -> str:
        return self.value
