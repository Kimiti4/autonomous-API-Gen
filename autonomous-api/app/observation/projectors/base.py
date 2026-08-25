"""The canonical-state binding port.

THIS is the single integration point for read access to platform state.
Everything downstream is written against this interface. Projectors are
pure functions: canonical → observation. They must never mutate.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CanonicalStateProvider(Protocol):
    """Read-only access to canonical platform state. Must never mutate."""

    async def get_isr(self) -> Any:
        """Return the canonical ISR object for the current architecture."""
        ...

    async def get_generation(self, generation: int) -> Any:
        """Return the canonical record for a generation (candidates, scores)."""
        ...

    async def get_lineage(self, candidate_id: str) -> Any:
        """Return the lineage record for a candidate."""
        ...


class ProjectionContract:
    """Registry of contract IDs + versions for provenance/capabilities."""

    ISR = ("platform.observation.isr", "1.0.0")
    FITNESS = ("platform.observation.fitness", "1.0.0")
    CANDIDATES = ("platform.observation.candidates", "1.0.0")
    LINEAGE = ("platform.observation.lineage", "1.0.0")