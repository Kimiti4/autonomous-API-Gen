"""
Frontend ISR Edge Types.

Defines edge types for relationships within the Frontend ISR Profile
and between Frontend and Backend ISR entities.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class FrontendEdgeType(str, Enum):
    """Frontend-specific edge types for the ISR graph."""

    COMPOSES = "frontend.composes"
    STYLES = "frontend.styles"
    INTERACTS = "frontend.interacts"
    RENDERS = "frontend.renders"
    NAVIGATES_TO = "frontend.navigates_to"
    REFERENCES_API = "frontend.references_api"
    REFERENCES_EVENT = "frontend.references_event"
    DECLARES_STATE = "frontend.declares_state"
    SATISFIES_A11Y = "frontend.satisfies_a11y"
    VARIES_BY = "frontend.varies_by"
    DERIVES_FROM = "frontend.derives_from"

    def __str__(self) -> str:
        return self.value
