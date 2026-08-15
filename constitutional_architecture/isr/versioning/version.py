"""
ISR Version Model.

Represents a single immutable version of an ISR with full metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class ISRVersion:
    """
    An immutable versioned snapshot of an ISR.

    Each version is identified by its content hash and tracks
    its position in the evolutionary lineage.
    """

    isr: ISR
    content_hash: str
    version_number: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_hash: Optional[str] = None
    mutation_id: Optional[str] = None
    mutation_description: str = ""
    fitness_vector: Optional[dict[str, float]] = None
    generation: int = 0
    tags: tuple[str, ...] = ()

    @property
    def is_root(self) -> bool:
        return self.parent_hash is None

    @property
    def short_hash(self) -> str:
        return self.content_hash[:12]

    @property
    def display_name(self) -> str:
        return f"ISR-v{self.version_number}-{self.short_hash}"
