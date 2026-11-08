"""ISR source selection for canonical orchestration (Checkpoint 058)."""
from __future__ import annotations

from enum import Enum


class IsrSourceMode(str, Enum):
    """Which ISR lineage the authority must consume."""

    HUMAN_BASELINE = "human_baseline"
    SYNTHESIZED_CANDIDATE = "synthesized_candidate"
    HUMAN_APPROVED_SYNTHESIZED = "human_approved_synthesized"
